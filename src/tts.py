"""tts.py — narration audio per scene. Edge-TTS -> gTTS -> Piper -> Coqui.

One WAV per scene so it can be synced to its visual. Output normalised to
~ -14 LUFS via ffmpeg loudnorm.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import config as C
from .utils import get_logger, run, have
from .fallback import try_chain

log = get_logger("tts")


# ---------------------------------------------------------------------------
# Providers (each writes an audio file to `out` and returns it)
# ---------------------------------------------------------------------------
def _edge(text: str, out: Path, reveal: bool = False) -> Path:
    import edge_tts

    rate = C.TTS_RATE_REVEAL if reveal else C.TTS_RATE
    mp3 = out.with_suffix(".mp3")

    async def _go():
        communicate = edge_tts.Communicate(
            text, C.TTS_VOICE, rate=rate,
            pitch=getattr(C, "TTS_PITCH", "+0Hz"),
            volume=getattr(C, "TTS_VOLUME", "+0%"),
        )
        await communicate.save(str(mp3))

    asyncio.run(_go())
    if not mp3.exists() or mp3.stat().st_size == 0:
        raise RuntimeError("edge-tts produced empty file")
    return mp3


def _gtts(text: str, out: Path, reveal: bool = False) -> Path:
    from gtts import gTTS

    mp3 = out.with_suffix(".mp3")
    gTTS(text=text, lang=C.GTTS_LANG, slow=False).save(str(mp3))
    if not mp3.exists() or mp3.stat().st_size == 0:
        raise RuntimeError("gTTS produced empty file")
    return mp3


def _piper(text: str, out: Path, reveal: bool = False) -> Path:
    # Requires piper binary + a voice model on PATH (optional backup).
    if not have("piper"):
        raise RuntimeError("piper not installed")
    wav = out.with_suffix(".wav")
    model = C.env("PIPER_MODEL", "")
    if not model:
        raise RuntimeError("no PIPER_MODEL configured")
    p = run(["bash", "-lc", f'echo {text!r} | piper --model "{model}" --output_file "{wav}"'])
    if not wav.exists():
        raise RuntimeError("piper produced no file")
    return wav


def _normalize(src: Path, dst: Path) -> Path:
    """Loudness-normalize to target and standardise to 48k mono WAV."""
    dst = dst.with_suffix(".wav")
    try:
        run([
            "ffmpeg", "-y", "-i", str(src),
            "-af", f"loudnorm=I={C.TARGET_LUFS_VOICE}:TP=-1.5:LRA=11",
            "-ar", "48000", "-ac", "1", str(dst),
        ], quiet=True)
    except Exception as e:  # noqa: BLE001
        log.warning("loudnorm failed (%s) — copying raw", e)
        run(["ffmpeg", "-y", "-i", str(src), "-ar", "48000", "-ac", "1", str(dst)], quiet=True)
    return dst


def synth_scene(text: str, out: Path, reveal: bool = False) -> Path:
    """Synthesize one scene's narration -> normalized 48k WAV at `out`."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    raw = try_chain(
        "tts",
        [
            ("edge-tts", lambda: _edge(text, out, reveal)),
            ("gtts", lambda: _gtts(text, out, reveal)),
            ("piper", lambda: _piper(text, out, reveal)),
        ],
    )
    return _normalize(raw, out)


def audio_duration(path: Path) -> float:
    """Duration in seconds via ffprobe (fallback to mutagen)."""
    try:
        p = run([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path),
        ], quiet=True)
        return float(p.stdout.strip())
    except Exception:
        try:
            from mutagen import File as MFile
            return float(MFile(str(path)).info.length)
        except Exception:
            return 0.0


def _edge_at_rate(text: str, out: Path, rate: str) -> Path:
    """Edge TTS with an explicit rate override (used to fit the CTA in <=10s)."""
    import edge_tts
    mp3 = out.with_suffix(".mp3")

    async def _go():
        c = edge_tts.Communicate(
            text, C.TTS_VOICE, rate=rate,
            pitch=getattr(C, "TTS_PITCH", "+0Hz"),
            volume=getattr(C, "TTS_VOLUME", "+0%"),
        )
        await c.save(str(mp3))

    asyncio.run(_go())
    if not mp3.exists() or mp3.stat().st_size == 0:
        raise RuntimeError("edge-tts CTA produced empty file")
    return mp3


def make_cta(out: Path, max_sec: float = 10.0):
    """Synthesize the subscribe/like CTA so it fits inside the outro (<= max_sec).

    Tries the full line at increasing speeds, then a shorter line, so the
    narration never overruns the 10s outro clip. Returns (wav_path, duration).
    """
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    attempts = [
        (C.OUTRO_CTA_TEXT, "+12%"), (C.OUTRO_CTA_TEXT, "+25%"),
        (C.OUTRO_CTA_TEXT, "+40%"),
        (C.OUTRO_CTA_SHORT, "+15%"), (C.OUTRO_CTA_SHORT, "+35%"),
    ]
    best = None
    for text, rate in attempts:
        try:
            raw = _edge_at_rate(text, out, rate)
        except Exception:
            try:
                raw = _gtts(text, out)   # backup voice
            except Exception:
                continue
        wav = _normalize(raw, out)
        dur = audio_duration(wav)
        if 0 < dur <= max_sec - 0.15:
            log.info("CTA fits: %.2fs (rate %s)", dur, rate)
            return wav, dur
        best = (wav, dur)
    # last resort: fastest short line, trimmed to fit
    if best and best[1] > max_sec:
        trimmed = out.with_name(out.stem + "_fit").with_suffix(".wav")
        run(["ffmpeg", "-y", "-i", str(best[0]), "-t", f"{max_sec-0.15:.2f}",
             "-ar", "48000", "-ac", "1", str(trimmed)], quiet=True, check=False)
        if trimmed.exists():
            return trimmed, audio_duration(trimmed)
    return best if best else (None, 0.0)
