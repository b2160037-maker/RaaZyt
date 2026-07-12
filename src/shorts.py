"""shorts.py -- 3 different promo Shorts per long video (File 1 Section 10).

Each Short: its own script/angle, vertical 1080x1920, ONE continuous Edge-TTS
voiceover across the whole clip (so narration never cuts out), fast visual cuts,
music. <=55s spoken.
"""
from __future__ import annotations

import math
from pathlib import Path

import config as C
from .utils import get_logger, extract_json
from . import script as script_mod
from . import tts, visuals, edit

log = get_logger("shorts")

SHORTS_PROMPT = """Long video topic: {TOPIC}. Long video link: {VIDEO_URL}.
3 alag-alag YouTube Shorts scripts do (each <= 50 sec spoken, Hinglish, no captions needed).
Har short ka angle alag ho:
  Short 1: SHOCK OPEN -- sabse crazy fact pehle 2 second me, phir "poori kahani main video me".
  Short 2: QUESTION HOOK -- ek darawna sawaal se shuru ("Kya tum jaante ho...?"), curiosity gap, phir CTA.
  Short 3: COUNTDOWN/LIST -- "3 cheezein jo {TOPIC} ke baare me darati hain", fast cuts, cliff at #1.
Har short ke pehle 1 second me scroll rokne wala hook hona chahiye. End me: "Poori mystery -- link/channel par."
STRICT JSON ONLY (array of 3):
[{{"style":"...","narration":"...","visual_queries":["...","...","..."],"end_cta":"..."}}]"""


def generate_scripts(topic: str, video_url: str = "") -> list[dict]:
    prompt = SHORTS_PROMPT.format(TOPIC=topic, VIDEO_URL=video_url or "channel par")
    data = extract_json(script_mod.call_llm(prompt))
    if isinstance(data, dict):
        data = data.get("shorts") or list(data.values())
    shorts = data[:3]
    while len(shorts) < 3:
        shorts.append({
            "style": "shock", "narration": f"{topic} ka sabse bada raaz -- poori kahani channel par.",
            "visual_queries": [topic], "end_cta": "Poori mystery -- channel par.",
        })
    return shorts


def build_one(short: dict, idx: int, out_dir: Path, day_dir: Path,
              music: Path | None = None) -> Path:
    """Build a single vertical short -> out_dir/shortN.mp4

    ONE continuous narration plays over fast-cutting visuals.
    """
    narration = short.get("narration", "").strip()
    queries = short.get("visual_queries") or [narration[:50]]
    work = day_dir / f"short{idx}_work"
    work.mkdir(parents=True, exist_ok=True)

    # 1) full narration audio (fast + confident via config rate/pitch)
    audio = tts.synth_scene(narration, work / "audio")
    total = tts.audio_duration(audio)
    if total <= 0:
        raise RuntimeError(f"short{idx}: empty narration audio")

    # 2) fetch a few distinct visuals, then show them as FAST cuts (~5s each)
    n_vis = max(1, min(len(queries), 4))
    fetched = []
    for i in range(n_vis):
        vpath = work / f"vis{i}"
        try:
            v = visuals.fetch_scene_visual(queries[i % len(queries)], "tense", vpath,
                                           w=C.SHORT_W, h=C.SHORT_H)
        except Exception as e:  # noqa: BLE001
            log.warning("short%d visual %d failed (%s) -- AI fallback", idx, i, e)
            v = visuals.ai_image(queries[i % len(queries)], vpath, C.SHORT_W, C.SHORT_H)
        fetched.append(v)

    n_seg = min(8, max(n_vis, round(total / 5.0)))  # more segments = faster cuts
    per = total / n_seg
    scenes = [{"visual": fetched[i % n_vis], "duration": per, "mood": "tense"}
              for i in range(n_seg)]

    out = out_dir / f"short{idx}.mp4"
    edit.build_video(scenes, out, vertical=True, voiceover=audio, music=music,
                     sting=None, crossfade=False)  # NOTE: no outro on Shorts
    return out


def build_all(topic: str, out_dir: Path, day_dir: Path, video_url: str = "",
              music: Path | None = None) -> list[dict]:
    scripts = generate_scripts(topic, video_url)
    results = []
    for i, sh in enumerate(scripts, start=1):
        try:
            path = build_one(sh, i, out_dir, day_dir, music=music)
            results.append({"idx": i, "script": sh, "path": str(path)})
        except Exception as e:  # noqa: BLE001
            log.error("short %d failed: %s", i, e)
    return results
