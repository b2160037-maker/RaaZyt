"""run_all.py -- 4:30 PM orchestrator (File 2 Section 5).

topic -> script -> tts -> visuals -> edit(long) -> thumbnail -> shorts
-> metadata -> QA gate -> upload long -> inject URL -> upload shorts -> notify.

Per-scene TTS + visual fetches run in parallel (VISUAL_WORKERS) so a flaky
image provider doesn't serialise the whole run. Wrapped in try/except with
per-stage logging. Nothing broken is uploaded.
"""
from __future__ import annotations

import datetime as dt
from datetime import timezone, timedelta
import random
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import config as C
from .utils import get_logger, write_json, read_json
from .fallback import USED_PROVIDERS
from . import topic as topic_mod
from . import script as script_mod
from . import tts, visuals, edit, thumbnail, shorts, metadata, qa, upload, notify, seo

log = get_logger("run_all")


def _pick_music():
    tracks = list(C.MUSIC_DIR.glob("*.mp3")) + list(C.MUSIC_DIR.glob("*.wav"))
    return random.choice(tracks) if tracks else None


def _scene_worker(i: int, sc: dict, day_dir: Path, reveal: bool):
    """Synthesize audio + fetch visual for ONE scene. Returns dict or None."""
    narr = (sc.get("narration") or "").strip()
    if not narr:
        return None
    try:
        audio = tts.synth_scene(narr, day_dir / f"aud_{i:03d}", reveal=reveal)
        dur = tts.audio_duration(audio)
        if dur <= 0:
            log.warning("scene %d has 0s audio -- skipping", i)
            return None
        if sc.get("host") and Path(C.HOST_CLIP).exists():
            vis = C.HOST_CLIP          # host to camera; edit.py loops/trims to narration
        else:
            try:
                vis = visuals.fetch_scene_visual(sc["visual_query"], sc.get("mood", "tense"),
                                                 day_dir / f"vis_{i:03d}")
            except Exception as e:  # noqa: BLE001
                log.warning("scene %d visual failed (%s) -- AI fallback from narration", i, e)
                vis = visuals.ai_image(sc["visual_query"], day_dir / f"vis_{i:03d}",
                                       C.LONG_W, C.LONG_H)
        return {"i": i, "visual": vis, "audio": audio, "duration": dur,
                "mood": sc.get("mood", "tense"), "narration": narr}
    except Exception as e:  # noqa: BLE001
        log.error("scene %d failed entirely: %s", i, e)
        return None


def _build_long_scenes(script: dict, day_dir: Path):
    """Synthesize audio + fetch visuals for every scene IN PARALLEL; return
    ordered scenes + total narration seconds."""
    twist_idx = script.get("twist_scene_index", -1)

    intro_beats = [
        {"narration": script["cold_open"], "visual_query": script["scenes"][0]["visual_query"],
         "mood": "reveal", "onscreen_seconds": 4},
        {"narration": script["hook_promise"],
         "visual_query": script["scenes"][0]["visual_query"],
         "mood": "tense", "onscreen_seconds": 6, "host": True},
    ]
    all_scenes = intro_beats + script["scenes"] + [
        {"narration": script.get("ending", ""), "visual_query": "dark reveal",
         "mood": "reveal", "onscreen_seconds": 6, "host": True},
        {"narration": script.get("cta", ""), "visual_query": "subscribe glow",
         "mood": "calm", "onscreen_seconds": 4, "host": True},
    ]

    def is_reveal(i, sc):
        return sc.get("mood") == "reveal" or i == (twist_idx + len(intro_beats))

    results = []
    workers = max(1, int(C.VISUAL_WORKERS))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(_scene_worker, i, sc, day_dir, is_reveal(i, sc))
                for i, sc in enumerate(all_scenes)]
        for f in futs:
            r = f.result()
            if r:
                results.append(r)

    results.sort(key=lambda r: r["i"])
    scenes_out = [{"visual": r["visual"], "audio": r["audio"],
                   "duration": r["duration"], "mood": r["mood"],
                   "narration": r.get("narration", "")} for r in results]
    total = sum(r["duration"] for r in results)
    log.info("built %d scenes in parallel (%d workers), %.1fs narration",
             len(scenes_out), workers, total)
    return scenes_out, total


IST = timezone(timedelta(hours=5, minutes=30))

PLAYLIST_BY_TYPE = {
    "unsolved_mystery": "Unsolved Mysteries in Hindi",
    "true_story": "Real Mysterious Stories",
    "mind_blowing_fact": "Mind Blowing Facts Hindi",
}


def _short_publish_at(idx: int):
    """Staggered release via YouTube scheduled publish (RFC3339 UTC, or None=now).
    short 1 -> now (public with the long video)
    short 2 -> +SHORT2_DELAY_HOURS
    short 3 -> next morning at SHORT3_HOUR_IST
    """
    now = dt.datetime.now(IST)
    if idx <= 1:
        return None
    if idx == 2:
        t = now + timedelta(hours=C.SHORT2_DELAY_HOURS)
    else:
        t = (now + timedelta(days=1)).replace(
            hour=C.SHORT3_HOUR_IST, minute=0, second=0, microsecond=0)
    if t <= now + timedelta(minutes=10):
        return None  # too close / in the past -> just publish now
    return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    today = dt.date.today().isoformat()
    day_dir = C.OUTPUT_DIR / today
    day_dir.mkdir(parents=True, exist_ok=True)

    try:
        state = topic_mod.load_state()
        if not state.get("topic") or state.get("date") != today:
            log.info("no fresh 6AM state -- picking topic now")
            state = topic_mod.announce()
        topic = state["topic"]
        slug = state["slug"]
        ttype = state.get("type", "unsolved_mystery")
        log.info("TOPIC: %s", topic)

        script = script_mod.generate(topic, ttype)
        write_json(day_dir / "script.json", script)

        # SEO: research the day's keywords (free autocomplete -> fallbacks)
        keywords = seo.research_keywords(topic, day_dir)

        music = _pick_music()
        # subscribe/like CTA voice for the fixed branded outro (<= 10s)
        cta_audio, cta_dur = tts.make_cta(day_dir / "cta_outro", max_sec=C.OUTRO_MAX_SEC)

        scenes, narration_sec = _build_long_scenes(script, day_dir)
        if not scenes:
            raise RuntimeError("no scenes built -- aborting")
        long_path = day_dir / "long.mp4"
        edit.build_video(scenes, long_path, vertical=False, music=music,
                         sting=C.SIGNATURE_STING,
                         outro_clip=C.OUTRO_CLIP, outro_voice=cta_audio)

        hook = (script.get("title_options") or [""])[0]
        thumb = thumbnail.get_thumbnail(topic, slug, day_dir, hook_text="SACH YA JHOOTH?",
                                        date=state.get("date", today))

        short_results = shorts.build_all(topic, day_dir, day_dir, video_url="", music=music)

        srt_path = seo.build_srt(scenes, day_dir / "captions.srt")
        chapters = seo.chapters_from_scenes(scenes)
        long_meta = metadata.build(script, topic, keywords=keywords, chapters=chapters)
        write_json(day_dir / "meta.json", long_meta)

        if not qa.run_gate(long_path, short_results, thumb, narration_sec, day_dir):
            raise RuntimeError("QA gate FAILED -- not uploading (see qa_report.txt)")

        result = upload.upload_video(long_path, long_meta)
        upload.set_thumbnail(result["id"], thumb)
        upload.upload_caption(result["id"], srt_path)  # viewer-off, SEO indexing
        primary_kw = keywords.get("primary", topic)
        upload.pin_comment(
            result["id"],
            f"Aapko kya lagta hai -- {topic} sach hai ya kahani? "
            f"Comment me batao. {primary_kw} #RaazFiles RAAZ KHULEGA")
        upload.add_to_playlist(result["id"], PLAYLIST_BY_TYPE.get(ttype,
                                                                  "Unsolved Mysteries in Hindi"))
        long_url = result["url"]

        short_links = []
        for sh in short_results:
            smeta = metadata.build_short(sh["script"], topic, long_url, sh["idx"], keywords=keywords)
            pub = _short_publish_at(sh["idx"])
            try:
                sres = upload.upload_video(Path(sh["path"]), smeta, publish_at=pub)
                when = "now" if not pub else f"scheduled {pub}"
                log.info("short %d uploaded (%s)", sh["idx"], when)
                short_links.append(f"{sres['url']} (live: {when})")
            except Exception as e:  # noqa: BLE001
                log.error("short %d upload failed: %s", sh["idx"], e)

        run_log = {
            "date": today, "topic": topic, "long_url": long_url,
            "short_urls": short_links, "providers": dict(USED_PROVIDERS),
        }
        write_json(day_dir / "run_log.json", run_log)
        notify.email_owner(
            f"Done: {topic}",
            f"Long: {long_url}\nShorts:\n" + "\n".join(short_links)
            + f"\n\nProviders used: {USED_PROVIDERS}",
        )
        log.info("ALL DONE  %s", long_url)
        return 0

    except Exception as e:  # noqa: BLE001
        tb = traceback.format_exc()
        log.error("RUN FAILED: %s\n%s", e, tb)
        (day_dir / "error.log").write_text(tb, encoding="utf-8")
        notify.email_owner(f"RAAZ FILES run failed ({today})",
                           f"Error: {e}\n\n{tb[-3000:]}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
