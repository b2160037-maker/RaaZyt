"""metadata.py -- SEO title, description, tags (Files 01 S11 + 03).

Tags are packed to YouTube's ~500-char budget (long AND Shorts). Title/desc/tags
front-load the researched PRIMARY keyword. Long descriptions include chapters
and the brand slogan. Everything stays keyword-rich but not spammy.
"""
from __future__ import annotations

import re

import config as C
from .utils import get_logger

log = get_logger("metadata")

SLOGAN = "Naye raaz roz -- Subscribe karo. RAAZ KHULEGA."
DISCLAIMER = (
    "Ye video entertainment aur educational purpose ke liye hai; "
    "kuch theories unverified hain / kaha jata hai."
)

EVERGREEN_TAGS = [
    "mystery", "unsolved mystery", "unsolved mysteries", "mystery in hindi",
    "hindi mystery", "mysteries", "unsolved", "rahasya", "raaz", "raaz files",
    "duniya ke raaz", "anokhe raaz", "facts", "amazing facts", "interesting facts",
    "mind blowing facts", "facts in hindi", "hindi facts", "random facts",
    "true story", "real story", "story", "kahani", "horror story", "scary story",
    "darawni kahani", "hinglish", "hindi", "scary", "horror", "creepy",
    "mysterious", "documentary", "hindi documentary", "knowledge", "gyan",
    "information", "educational", "history", "ancient mystery", "world mysteries",
    "paranormal", "supernatural", "unexplained", "conspiracy", "secrets",
    "hidden truth", "sach", "viral video", "trending", "india", "bharat",
]

BASE_HASHTAGS = ["#RaazFiles", "#UnsolvedMystery", "#Hinglish", "#Mystery",
                 "#Facts", "#Hindi", "#Story", "#Rahasya", "#RealStory",
                 "#Documentary", "#Mysteries"]


def _clean(text: str) -> str:
    return re.sub(r"[^\w\s]", "", text or "").strip().lower()


def _hashtag(s: str) -> str:
    parts = _clean(s).split()
    return "#" + "".join(p.capitalize() for p in parts) if parts else ""


def _topic_tags(topic: str) -> list[str]:
    tl = _clean(topic)
    words = [w for w in tl.split() if len(w) > 3]
    suffixes = ["mystery", "in hindi", "hindi", "explained", "facts", "story",
                "real story", "documentary", "raaz", "rahasya", "ka sach",
                "ka raaz", "unsolved", "history", "reality", "truth", "kahani"]
    tags = [tl] + [f"{tl} {s}" for s in suffixes] + [f"unsolved {tl}"]
    tags += words + [f"{w} facts" for w in words] + [f"{w} mystery" for w in words]
    return tags


def _pack_tags(pool: list[str], limit: int = 490) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    total = 0
    for t in pool:
        t = (t or "").strip().lower()
        if not t or t in seen or len(t) > 60:
            continue
        cost = len(t) + 1 + (2 if " " in t else 0)
        if total + cost > limit:
            continue
        out.append(t)
        seen.add(t)
        total += cost
    return out


def _hashtags(topic: str, extra: list[str] | None = None) -> list[str]:
    pool = [_hashtag(topic)] + (extra or []) + BASE_HASHTAGS
    seen: set[str] = set()
    out: list[str] = []
    for h in pool:
        hl = h.lower()
        if h and len(h) > 1 and hl not in seen:
            out.append(h)
            seen.add(hl)
    return out[:15]


def _clip_title(hook: str) -> str:
    base = f" | {C.CHANNEL_NAME}"
    room = 62 - len(base)               # <= ~60 chars so mobile doesn't cut it
    hook = hook.strip().rstrip(".")
    if len(hook) > room:
        hook = hook[: room - 1].rstrip() + "..."
    return f"{hook}{base}"


def _pick_title(title_opts: list[str], primary: str) -> str:
    """Prefer a title that contains the primary keyword; else the richest one."""
    if primary:
        for t in title_opts:
            if primary.lower() in t.lower():
                return _clip_title(t)
    return _clip_title(max(title_opts, key=len))


def build(script: dict, topic: str, *, video_url: str = "",
          keywords: dict | None = None, chapters: list[str] | None = None) -> dict:
    kw = keywords or {}
    primary = kw.get("primary") or topic
    secondary = kw.get("secondary") or []
    long_tail = kw.get("long_tail") or []

    title_opts = script.get("title_options") or [topic]
    title = _pick_title(title_opts, primary)

    desc_hook = (script.get("description") or script.get("hook_promise", "")).strip()
    ending_cta = script.get("cta", "Subscribe karo RAAZ FILES.")
    hashtags = _hashtags(topic)

    # First 2 lines carry the primary keyword (shown in search results).
    lead = f"{primary} - {desc_hook}" if primary.lower() not in desc_hook.lower() else desc_hook

    parts = [
        lead,
        "",
        f"Is video mein: {topic} se judi unsolved mystery, real story aur "
        f"mind-blowing facts -- poori kahani Hinglish mein, {C.CHANNEL_NAME} par.",
    ]
    if video_url:
        parts.append(f"\nPoori video: {video_url}")
    if chapters:
        parts += ["", "Chapters:", *chapters]
    parts += [
        "",
        "Aise aur raaz, rahasya aur sacchi kahaniyon ke liye channel ko "
        "SUBSCRIBE karo aur bell icon dabao.",
        "",
        ending_cta,
        SLOGAN,
        "",
        DISCLAIMER,
        "",
        " ".join(hashtags),
    ]
    description = "\n".join(parts)

    # tag pool: PRIMARY first, then secondary + long-tail, then script + topic + evergreen
    pool = ([primary] + secondary + long_tail + (script.get("tags") or [])
            + _topic_tags(topic) + EVERGREEN_TAGS)
    tags = _pack_tags(pool, limit=490)
    log.info("long tags: %d (%d chars), primary=%r",
             len(tags), sum(len(t) + 1 for t in tags), primary)

    return {
        "title": title,
        "description": description,
        "tags": tags,
        "categoryId": C.YT_CATEGORY_ID,
        "privacyStatus": C.YT_PRIVACY,
        "defaultLanguage": "hi",
        "madeForKids": False,
    }


def build_short(short: dict, topic: str, video_url: str, idx: int,
                keywords: dict | None = None) -> dict:
    kw = keywords or {}
    primary = kw.get("primary") or topic
    secondary = kw.get("secondary") or []
    long_tail = kw.get("long_tail") or []

    title = f"{topic} ka RAAZ \U0001F631 #Shorts | {C.CHANNEL_NAME}"[:100]
    hashtags = _hashtags(topic, extra=["#Shorts", "#ytshorts", "#viral", "#trending"])

    desc = "\n".join([
        f"{primary} - " + short.get("end_cta",
                                    f"{topic} ka poora sach jaanne ke liye video dekho."),
        "",
        f"Poori mystery yahan dekho: {video_url}" if video_url else
        f"Poori mystery {C.CHANNEL_NAME} channel par.",
        "",
        f"{topic} se judi unsolved mystery, facts aur real story -- Hinglish mein.",
        "",
        "SUBSCRIBE karo RAAZ FILES. RAAZ KHULEGA.",
        "",
        " ".join(hashtags),
    ])

    pool = (["shorts", "youtube shorts", "ytshorts", "viral shorts", "trending shorts",
             f"{_clean(topic)} shorts", primary] + secondary + long_tail
            + [short.get("style", "short")] + _topic_tags(topic) + EVERGREEN_TAGS)
    tags = _pack_tags(pool, limit=490)
    log.info("short%d tags: %d (%d chars)", idx, len(tags),
             sum(len(t) + 1 for t in tags))

    return {
        "title": title,
        "description": desc,
        "tags": tags,
        "categoryId": C.YT_CATEGORY_ID,
        "privacyStatus": C.YT_PRIVACY,
        "defaultLanguage": "hi",
        "madeForKids": False,
    }
