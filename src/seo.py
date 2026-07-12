"""seo.py -- free YouTube SEO helpers (File 03).

- Keyword research: YouTube autocomplete (primary) -> Google autocomplete
  (backup) -> pytrends (optional). Saves output/DATE/keywords.json.
- SRT caption builder from the exact narration + measured scene durations
  (viewer-off, but YouTube indexes it for search).
- Chapters/timestamps for the description (long videos >= 4 min).
- Weekly pass: competitor keyword scan + YouTube Analytics feedback (best-effort).

Everything is best-effort and network-resilient: if a source is down we fall
back, and if all fail we derive keywords from the topic so the run never breaks.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import urllib.parse

import config as C
from .utils import get_logger, http_get, read_json, write_json, slugify

log = get_logger("seo")

SLOGAN = "RAAZ KHULEGA"


# ---------------------------------------------------------------------------
# Keyword research
# ---------------------------------------------------------------------------
def _autocomplete(query: str, youtube: bool = True) -> list[str]:
    ds = "yt" if youtube else ""
    url = ("https://suggestqueries.google.com/complete/search"
           f"?client=firefox&ds={ds}&q=" + urllib.parse.quote(query))
    try:
        r = http_get(url, timeout=15, retries=1)
        data = json.loads(r.text)
        # firefox client -> [query, [suggestions...]]
        if isinstance(data, list) and len(data) > 1 and isinstance(data[1], list):
            return [s for s in data[1] if isinstance(s, str)]
    except Exception as e:  # noqa: BLE001
        log.debug("autocomplete failed for %r (yt=%s): %s", query, youtube, e)
    return []


def _pytrends_related(topic: str) -> list[str]:
    try:
        from pytrends.request import TrendReq
        py = TrendReq(hl="en-IN", tz=330)
        py.build_payload([topic], timeframe="today 12-m", geo="IN")
        out = []
        rel = py.related_queries().get(topic, {})
        for key in ("rising", "top"):
            df = rel.get(key)
            if df is not None:
                out += [str(x) for x in df["query"].tolist()[:10]]
        return out
    except Exception as e:  # noqa: BLE001
        log.debug("pytrends failed: %s", e)
        return []


def research_keywords(topic: str, day_dir=None) -> dict:
    """Return {primary, secondary[], long_tail[], all[]} and save keywords.json."""
    seeds = [topic, f"{topic} mystery", f"{topic} in hindi", f"{topic} facts",
             f"{topic} real story"]
    suggestions: list[str] = []
    for seed in seeds:
        suggestions += _autocomplete(seed, youtube=True)
    if len(suggestions) < 8:  # YT thin -> Google web autocomplete
        for seed in seeds[:3]:
            suggestions += _autocomplete(seed, youtube=False)
    suggestions += _pytrends_related(topic)

    # de-dupe (case-insensitive), keep order
    seen, phrases = set(), []
    for s in suggestions:
        s = re.sub(r"\s+", " ", s).strip().lower()
        if s and s not in seen and len(s) <= 70:
            seen.add(s)
            phrases.append(s)

    tl = topic.lower()
    if not phrases:  # total fallback: derive from topic
        phrases = [tl, f"{tl} mystery", f"{tl} in hindi", f"{tl} facts",
                   f"{tl} real story", f"unsolved {tl}", f"{tl} documentary"]

    # primary = the phrase most similar to the topic (else first)
    primary = next((p for p in phrases if tl in p), phrases[0])
    secondary = [p for p in phrases if p != primary][:5]
    long_tail = [p for p in phrases
                 if any(k in p for k in ("hindi", "mystery", "story", "facts", "real"))][:12]

    result = {"topic": topic, "primary": primary, "secondary": secondary,
              "long_tail": long_tail, "all": phrases}
    if day_dir is not None:
        try:
            write_json(day_dir / "keywords.json", result)
        except Exception:  # noqa: BLE001
            pass
    log.info("keywords: primary=%r, %d total", primary, len(phrases))
    return result


# ---------------------------------------------------------------------------
# SRT captions (viewer-off, SEO indexing)
# ---------------------------------------------------------------------------
def _srt_time(sec: float) -> str:
    if sec < 0:
        sec = 0
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int(round((sec - int(sec)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_srt(items: list[dict], out_path) -> "Path":  # noqa: F821
    """items: [{'narration': str, 'duration': float}] in play order."""
    from pathlib import Path
    out_path = Path(out_path)
    lines, t = [], 0.0
    idx = 1
    for it in items:
        text = (it.get("narration") or "").strip()
        dur = float(it.get("duration") or 0)
        if not text or dur <= 0:
            t += dur
            continue
        start, end = t, t + dur
        lines += [str(idx), f"{_srt_time(start)} --> {_srt_time(end)}", text, ""]
        idx += 1
        t = end
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------------
# Chapters for the description (>= 4 min videos only, YouTube rules)
# ---------------------------------------------------------------------------
def chapters_from_scenes(items: list[dict], min_video_sec: float = 240.0) -> list[str]:
    total = sum(float(i.get("duration") or 0) for i in items)
    if total < min_video_sec:
        return []
    # aim for ~6-8 chapters, each >= 10s, first at 00:00
    target = min(8, max(3, int(total // 90)))
    step = total / target
    chapters, t, next_mark, made = [], 0.0, 0.0, 0
    for it in items:
        dur = float(it.get("duration") or 0)
        if t >= next_mark - 0.01 and made < target:
            label = _chapter_label(it.get("narration", ""), made)
            mm, ss = int(t // 60), int(t % 60)
            chapters.append(f"{mm:02d}:{ss:02d} {label}")
            made += 1
            next_mark += step
        t += dur
    # YouTube needs the first chapter at 00:00
    if chapters and not chapters[0].startswith("00:00"):
        chapters[0] = "00:00 " + chapters[0].split(" ", 1)[1]
    return chapters if len(chapters) >= 3 else []


def _chapter_label(narration: str, i: int) -> str:
    words = re.sub(r"[^\w\s]", "", narration or "").split()
    if len(words) >= 2:
        return " ".join(words[:4]).title()
    return ["Shuruaat", "Raaz", "Mod", "Twist", "Sach", "Sabse Bada Sach",
            "Ending", "Ant"][i % 8]


# ---------------------------------------------------------------------------
# Weekly pass (competitor scan + analytics feedback) -- best effort
# ---------------------------------------------------------------------------
def competitor_pass() -> list[str]:
    """Search the niche, ask the model for gap topics, add to topics.json."""
    try:
        from . import upload, script as script_mod
        yt = upload._service()
        seen_titles = []
        for kw in ("unsolved mystery hindi", "mysterious facts hindi", "raaz"):
            res = yt.search().list(part="snippet", q=kw, type="video",
                                   maxResults=10, order="viewCount").execute()
            seen_titles += [it["snippet"]["title"] for it in res.get("items", [])]
        prompt = (
            "Yeh top-ranking mystery video titles hain:\n" + "\n".join(seen_titles[:25])
            + "\n\nInme se keyword/topic GAPS dhoondo jinpe ek Hinglish mystery channel "
            "rank kar sake. 20 fresh unsolved-mystery / true-story / mind-blowing-fact "
            "topics do jinme high search + low competition ho. STRICT JSON: "
            '{"topics":[{"topic":"...","type":"unsolved_mystery|true_story|mind_blowing_fact"}]}'
        )
        from .utils import extract_json
        data = extract_json(script_mod.call_llm(prompt))
        report_topics = [t for t in data.get("topics", []) if t.get("topic")]

        today = dt.date.today().isoformat()
        bank = read_json(C.TOPICS_FILE, {"topics": []})
        used = {u.get("slug") for u in
                read_json(C.USED_TOPICS_FILE, {"used": []}).get("used", [])}
        by_slug = {slugify(t["topic"]): t for t in bank.get("topics", [])}

        added, refreshed = [], []
        for t in report_topics:
            sl = slugify(t["topic"])
            if sl in used:
                continue                     # already a video -> NEVER reuse
            if sl in by_slug:
                by_slug[sl]["added"] = today  # repeated in a new report -> bump priority
                refreshed.append(t["topic"])
            else:
                entry = {"topic": t["topic"],
                         "type": t.get("type", "unsolved_mystery"),
                         "source": "seo", "added": today}
                bank["topics"].append(entry)
                by_slug[sl] = entry
                added.append(t["topic"])
        write_json(C.TOPICS_FILE, bank)

        # structured report of THIS week's usable topics (newest report wins priority)
        write_json(C.OUTPUT_DIR / "seo_report.json",
                   {"date": today, "topics": report_topics,
                    "added": added, "refreshed": refreshed})
        log.info("competitor pass: +%d new, %d refreshed (used skipped)",
                 len(added), len(refreshed))
        return added
    except Exception as e:  # noqa: BLE001
        log.warning("competitor pass failed: %s", e)
        return []


def analytics_pass(days: int = 28) -> dict:
    """Pull channel analytics (needs yt-analytics.readonly scope). Best effort."""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        info = json.loads(C.YT_TOKEN_JSON)
        creds = Credentials.from_authorized_user_info(info)
        if not creds.valid and creds.refresh_token:
            creds.refresh(Request())
        ya = build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False)
        end = dt.date.today()
        start = end - dt.timedelta(days=days)
        rep = ya.reports().query(
            ids="channel==MINE", startDate=start.isoformat(), endDate=end.isoformat(),
            metrics="views,estimatedMinutesWatched,averageViewPercentage,likes,comments",
            dimensions="day",
        ).execute()
        return rep
    except Exception as e:  # noqa: BLE001
        log.warning("analytics pass failed (scope/token?): %s", e)
        return {}


def weekly() -> int:
    from . import notify
    added = competitor_pass()
    stats = analytics_pass()
    report = C.OUTPUT_DIR / "seo_report.txt"
    lines = [f"WEEKLY SEO REPORT ({dt.date.today().isoformat()})", "=" * 40,
             f"New topics added from competitor gaps: {len(added)}"]
    lines += [f"  - {t}" for t in added]
    if stats.get("rows"):
        lines.append("")
        lines.append(f"Analytics rows (last 28 days): {len(stats['rows'])}")
        cols = [h["name"] for h in stats.get("columnHeaders", [])]
        lines.append("cols: " + ", ".join(cols))
    else:
        lines.append("Analytics: unavailable (add yt-analytics.readonly scope via get_token.py)")
    report.write_text("\n".join(lines), encoding="utf-8")
    notify.email_owner("Weekly SEO report -- RAAZ FILES", "\n".join(lines))
    log.info("weekly SEO pass done -> %s", report)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--weekly", action="store_true")
    ap.add_argument("--keywords", metavar="TOPIC")
    args = ap.parse_args(argv)
    if args.weekly:
        return weekly()
    if args.keywords:
        print(json.dumps(research_keywords(args.keywords), ensure_ascii=False, indent=2))
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
