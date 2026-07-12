"""edit.py -- assemble scenes into the final video (MoviePy + FFmpeg).

Ken Burns on stills is pre-rendered with FFmpeg's zoompan (C-speed) instead of
MoviePy's slow per-frame Python resize -- this is the big render speed-up.
MoviePy then only concatenates clips, mixes audio, and appends the fixed outro.
"""
from __future__ import annotations

import json
import logging
import os
import warnings
from pathlib import Path

import numpy as np

import config as C
from .utils import get_logger, run, have

log = get_logger("edit")

warnings.filterwarnings("ignore", category=UserWarning, module="moviepy")
logging.getLogger("py.warnings").setLevel(logging.ERROR)


def _make_render_logger(label: str):
    """A clean render progress printer: prints "% frames ETA" every ~5%.
    Works both on screen and piped to a log file. Falls back to MoviePy's bar."""
    try:
        import time
        from proglog import ProgressBarLogger

        class _RL(ProgressBarLogger):
            def __init__(self):
                super().__init__()
                self._t0 = None
                self._last = -100.0

            def bars_callback(self, bar, attr, value, old_value=None):
                if attr != "index":
                    return
                total = self.bars[bar].get("total") or 0
                if not total:
                    return
                if self._t0 is None:
                    self._t0 = time.time()
                pct = value * 100.0 / total
                if pct - self._last < 5 and value < total:
                    return
                self._last = pct
                el = time.time() - self._t0
                eta = int(el / value * (total - value)) if value > 0 else 0
                m, s = divmod(eta, 60)
                filled = int(pct / 5)
                bar_str = "#" * filled + "-" * (20 - filled)
                print(f"[render {label}] [{bar_str}] {pct:5.1f}%  "
                      f"{value}/{total} frames  ETA {m:02d}:{s:02d}", flush=True)

        return _RL()
    except Exception:
        return "bar"

_PIL_PATCHED = False


def _patch_pil():
    global _PIL_PATCHED
    if _PIL_PATCHED:
        return
    try:
        from PIL import Image
        resampling = getattr(Image, "Resampling", Image)
        for old, new in (("ANTIALIAS", "LANCZOS"), ("BICUBIC", "BICUBIC"),
                         ("BILINEAR", "BILINEAR"), ("NEAREST", "NEAREST"),
                         ("LANCZOS", "LANCZOS")):
            if not hasattr(Image, old) and hasattr(resampling, new):
                setattr(Image, old, getattr(resampling, new))
    except Exception as e:  # noqa: BLE001
        log.warning("PIL patch skipped: %s", e)
    _PIL_PATCHED = True


def _mp():
    _patch_pil()
    import moviepy.editor as mpy
    return mpy


def _ken_burns_ffmpeg(img: Path, duration: float, w: int, h: int) -> Path:
    """Render a slow zoom (Ken Burns) on a still image to an mp4 using FFmpeg.
    Fast (C-speed) -- avoids MoviePy's per-frame Python resize bottleneck."""
    img = Path(img)
    out = img.with_name(img.stem + "_kb.mp4")
    frames = max(1, round(duration * C.FPS))
    zinc = 0.15 / frames  # 1.0 -> ~1.15 over the clip
    vf = (
        f"scale={w*2}:{h*2}:force_original_aspect_ratio=increase,"
        f"crop={w*2}:{h*2},"
        f"zoompan=z='min(zoom+{zinc:.6f},1.15)':d={frames}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={C.FPS},setsar=1"
    )
    run(["ffmpeg", "-y", "-loop", "1", "-i", str(img), "-t", f"{duration:.3f}",
         "-r", str(C.FPS), "-vf", vf, "-c:v", "libx264", "-preset", "veryfast",
         "-crf", "16", "-pix_fmt", "yuv420p", str(out)], quiet=True, check=True)
    return out


def _make_visual_clip(path: Path, duration: float, w: int, h: int):
    mpy = _mp()
    path = Path(path)
    is_video = path.suffix.lower() in (".mp4", ".mov", ".webm", ".mkv")
    if is_video:
        clip = mpy.VideoFileClip(str(path)).without_audio()
        if clip.duration < duration:
            clip = mpy.vfx.loop(clip, duration=duration)
        clip = clip.subclip(0, duration)
        clip = clip.resize(height=h).on_color(size=(w, h), color=(0, 0, 0),
                                              pos=("center", "center"))
        return clip.set_fps(C.FPS)
    # STILL image -> Ken Burns via FFmpeg (fast), then load the mp4
    try:
        kb = _ken_burns_ffmpeg(path, duration, w, h)
        return mpy.VideoFileClip(str(kb)).without_audio().set_fps(C.FPS)
    except Exception as e:  # noqa: BLE001
        log.warning("ffmpeg ken-burns failed (%s) -- static image fallback", e)
        base = mpy.ImageClip(str(path)).set_duration(duration)
        base = base.resize(height=h) if base.h < h else base.resize(width=w)
        return mpy.CompositeVideoClip([base.set_position(("center", "center"))],
                                      size=(w, h)).set_duration(duration).set_fps(C.FPS)


def _append_outro(content, w: int, h: int, vertical: bool,
                  outro_path: Path, outro_voice: Path | None):
    mpy = _mp()
    outro = mpy.VideoFileClip(str(outro_path))
    orig_audio = outro.audio
    odur = float(outro.duration)

    if vertical:
        scaled = outro.resize(width=w)
        bg = mpy.ColorClip(size=(w, h), color=(0, 0, 0)).set_duration(odur)
        ov = mpy.CompositeVideoClip(
            [bg, scaled.set_position(("center", "center"))], size=(w, h)
        ).set_duration(odur)
    else:
        ov = outro.resize((w, h))
    ov = ov.set_fps(C.FPS)

    if orig_audio is not None and outro_voice and Path(outro_voice).exists():
        from moviepy.audio.AudioClip import concatenate_audioclips
        narr = mpy.AudioFileClip(str(outro_voice))
        nd = min(float(narr.duration), odur)
        ducked = orig_audio.subclip(0, nd).volumex(C.OUTRO_DUCK_FACTOR)
        parts = [ducked]
        if odur - nd > 0.05:
            parts.append(orig_audio.subclip(nd, odur))
        orig_mix = concatenate_audioclips(parts) if len(parts) > 1 else ducked
        mixed = mpy.CompositeAudioClip([orig_mix, narr.set_start(0.0)]).set_duration(odur)
        ov = ov.set_audio(mixed)
    elif orig_audio is not None:
        ov = ov.set_audio(orig_audio)

    final = mpy.concatenate_videoclips([content, ov], method="compose")
    return final, odur


def build_video(scenes: list[dict], out_path: Path, *, vertical: bool = False,
                music: Path | None = None, sting: Path | None = None,
                voiceover: Path | None = None, crossfade: bool = True,
                outro_clip: Path | None = None, outro_voice: Path | None = None) -> Path:
    """Build a video from scenes and append the fixed branded outro."""
    mpy = _mp()
    w, h = (C.SHORT_W, C.SHORT_H) if vertical else (C.LONG_W, C.LONG_H)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    xfade = C.CROSSFADE_SEC if crossfade else 0.0

    clips = []
    for i, sc in enumerate(scenes):
        dur = float(sc["duration"])
        vis = _make_visual_clip(Path(sc["visual"]), dur, w, h)
        if voiceover:
            clip = vis
        else:
            aud_full = mpy.AudioFileClip(str(sc["audio"]))
            clip = vis.set_audio(aud_full.subclip(0, min(aud_full.duration, dur)))
        if i > 0 and xfade:
            clip = clip.crossfadein(xfade)
        clips.append(clip)

    if len(clips) > 1:
        video = mpy.concatenate_videoclips(clips, method="compose", padding=-xfade)
    else:
        video = clips[0]

    if voiceover and Path(voiceover).exists():
        voice = mpy.AudioFileClip(str(voiceover))
        if video.duration < voice.duration - 0.05:
            video = video.set_duration(voice.duration)
        layers_audio = [voice]
    else:
        layers_audio = [video.audio] if video.audio is not None else []

    if sting and Path(sting).exists() and not vertical:
        try:
            layers_audio.append(mpy.AudioFileClip(str(sting)).volumex(0.9).set_start(3.0))
        except Exception as e:  # noqa: BLE001
            log.warning("sting overlay failed: %s", e)

    if music and Path(music).exists():
        try:
            m = mpy.AudioFileClip(str(music))
            if m.duration < video.duration:
                m = mpy.afx.audio_loop(m, duration=video.duration)
            layers_audio.append(m.subclip(0, video.duration).volumex(0.18))
        except Exception as e:  # noqa: BLE001
            log.warning("music mix failed: %s", e)

    if layers_audio:
        video = video.set_audio(mpy.CompositeAudioClip(layers_audio))

    content = video
    content_sec = float(content.duration)
    final = content
    outro_sec = 0.0
    if outro_clip and Path(outro_clip).exists():
        try:
            final, outro_sec = _append_outro(content, w, h, vertical,
                                              Path(outro_clip), outro_voice)
        except Exception as e:  # noqa: BLE001
            log.error("outro append FAILED (%s) -- rendering without outro", e)
            final = content
    elif outro_clip:
        log.error("outro clip not found at %s -- rendering without outro", outro_clip)

    final.write_videofile(
        str(out_path), fps=C.FPS, codec="libx264", audio_codec="aac",
        ffmpeg_params=["-crf", str(C.VIDEO_CRF), "-pix_fmt", "yuv420p"],
        threads=(os.cpu_count() or 4), preset="medium",
        logger=_make_render_logger(out_path.name),
    )
    try:
        Path(str(out_path) + ".meta.json").write_text(json.dumps({
            "content_sec": round(content_sec, 2), "outro_sec": round(outro_sec, 2),
            "total_sec": round(float(final.duration), 2), "vertical": vertical,
        }), encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

    for c in clips:
        try:
            c.close()
        except Exception:
            pass
    log.info("rendered %s (content %.1fs + outro %.1fs)", out_path.name, content_sec, outro_sec)
    return out_path
