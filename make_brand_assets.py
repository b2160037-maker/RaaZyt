"""make_brand_assets.py — generate the reusable brand assets ONCE (all free).

Creates (only if missing — won't overwrite files you dropped yourself):
    assets/brand/signature_sting.wav   1.5s: bass whoosh + heartbeat + whispered name
    assets/brand/logo_sting.mp4         ~1.5s animated wordmark + sting audio
    assets/brand/avatar.png             1024x1024 channel avatar (AI)
    assets/brand/banner.png             2048x1152 channel banner (AI)

Run once locally (or let it run in Actions the first time):
    pip install -r requirements.txt
    sudo apt-get install -y ffmpeg
    python make_brand_assets.py
"""
from __future__ import annotations

import asyncio
import math
import struct
import wave
from pathlib import Path

import config as C
from src.utils import get_logger, run, have

log = get_logger("brand")


# ---------------------------------------------------------------------------
# 1. Signature sting audio (procedural — no downloads needed)
# ---------------------------------------------------------------------------
def make_signature_sting(dst: Path = C.SIGNATURE_STING) -> Path:
    if dst.exists():
        log.info("signature_sting.wav already exists — keeping it")
        return dst
    sr = 48000
    dur = 1.5
    n = int(sr * dur)
    samples = []
    for i in range(n):
        t = i / sr
        # low bass whoosh: rising sine 40->90 Hz with fade
        f = 40 + 50 * (t / dur)
        whoosh = math.sin(2 * math.pi * f * t) * math.exp(-2.2 * t)
        # two heartbeats "dhak-dhak" at 0.2s and 0.55s
        beat = 0.0
        for onset in (0.2, 0.55):
            if t >= onset:
                dt = t - onset
                beat += math.sin(2 * math.pi * 60 * dt) * math.exp(-30 * dt)
        val = 0.55 * whoosh + 0.5 * beat
        val = max(-1.0, min(1.0, val))
        samples.append(int(val * 32767))
    with wave.open(str(dst), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(b"".join(struct.pack("<h", s) for s in samples))
    log.info("wrote %s", dst)
    return dst


async def _whisper_name(dst: Path):
    import edge_tts
    c = edge_tts.Communicate(C.CHANNEL_NAME, C.TTS_VOICE, rate="-20%", volume="-10%")
    await c.save(str(dst))


def add_whisper_to_sting():
    """Best-effort: mix a whispered channel name over the sting."""
    try:
        whisper_mp3 = C.BRAND / "_whisper.mp3"
        asyncio.run(_whisper_name(whisper_mp3))
        mixed = C.BRAND / "_sting_mixed.wav"
        run(["ffmpeg", "-y", "-i", str(C.SIGNATURE_STING), "-i", str(whisper_mp3),
             "-filter_complex",
             "[1:a]adelay=700|700,volume=0.6[w];[0:a][w]amix=inputs=2:duration=first",
             "-ar", "48000", str(mixed)], check=False, quiet=True)
        if mixed.exists() and mixed.stat().st_size > 0:
            mixed.replace(C.SIGNATURE_STING)
        whisper_mp3.unlink(missing_ok=True)
    except Exception as e:  # noqa: BLE001
        log.warning("whisper mix skipped: %s", e)


# ---------------------------------------------------------------------------
# 2. Logo sting video (wordmark fade + sting audio)
# ---------------------------------------------------------------------------
def make_logo_sting(dst: Path = C.LOGO_STING) -> Path:
    if dst.exists():
        log.info("logo_sting.mp4 already exists — keeping it")
        return dst
    if not have("ffmpeg"):
        log.warning("ffmpeg missing — cannot build logo sting")
        return dst
    font = _find_font()
    fontfile = f":fontfile='{font}'" if font else ""
    # 1.6s black bg, channel name fades in with a teal glow, sting audio under it.
    vf = (
        f"drawtext=text='{C.CHANNEL_NAME}'"
        f"{fontfile}:fontcolor=0x33e6d0:fontsize=120:x=(w-tw)/2:y=(h-th)/2:"
        f"alpha='if(lt(t,0.3),t/0.3,1)'"
    )
    run(["ffmpeg", "-y",
         "-f", "lavfi", "-i", f"color=c=black:s={C.LONG_W}x{C.LONG_H}:d=1.6",
         "-i", str(C.SIGNATURE_STING),
         "-vf", vf, "-r", str(C.FPS), "-shortest",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(dst)],
        check=False)
    log.info("wrote %s", dst)
    return dst


def _find_font():
    for c in (C.FONTS_DIR / "Anton-Regular.ttf",
              C.FONTS_DIR / "BebasNeue-Regular.ttf",
              Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")):
        if Path(c).exists():
            return str(c)
    return None


# ---------------------------------------------------------------------------
# 3. Avatar + banner (AI, free)
# ---------------------------------------------------------------------------
def make_avatar(dst: Path = C.AVATAR):
    if dst.exists():
        return dst
    from src import visuals
    prompt = ("channel logo, a black mysterious book/file snapping open with a glowing "
              "teal-orange eye, dark cinematic, emblem, centered, no text")
    try:
        img = visuals.ai_image(prompt, dst.with_suffix(""), 1024, 1024)
        _square(img, dst, 1024)
    except Exception as e:  # noqa: BLE001
        log.warning("avatar gen failed: %s", e)
    return dst


def make_banner(dst: Path = C.BANNER):
    if dst.exists():
        return dst
    from src import visuals
    prompt = ("youtube channel banner, dark moody mysterious files and secrets theme, "
              "teal orange rim light, cinematic fog, wide cinematic, no text")
    try:
        img = visuals.ai_image(prompt, dst.with_suffix(""), 2048, 1152)
        _resize(img, dst, 2048, 1152)
    except Exception as e:  # noqa: BLE001
        log.warning("banner gen failed: %s", e)
    return dst


def _square(src, dst, size):
    from PIL import Image
    Image.open(src).convert("RGB").resize((size, size)).save(dst, "PNG")


def _resize(src, dst, w, h):
    from PIL import Image
    Image.open(src).convert("RGB").resize((w, h)).save(dst, "PNG")


def main():
    make_signature_sting()
    add_whisper_to_sting()
    make_logo_sting()
    make_avatar()
    make_banner()
    log.info("brand assets ready in %s", C.BRAND)


if __name__ == "__main__":
    main()
