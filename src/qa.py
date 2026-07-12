"""qa.py -- quality gate (File 1 Section 14). Nothing uploads unless this passes."""
from __future__ import annotations

import json
from pathlib import Path

import config as C
from .utils import get_logger, run

log = get_logger("qa")


def _probe(path: Path) -> dict:
    p = run([
        "ffprobe", "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", str(path),
    ], quiet=True, check=False)
    try:
        return json.loads(p.stdout)
    except Exception:
        return {}


def _video_stream(info: dict) -> dict:
    for s in info.get("streams", []):
        if s.get("codec_type") == "video":
            return s
    return {}


def _audio_stream(info: dict) -> dict:
    for s in info.get("streams", []):
        if s.get("codec_type") == "audio":
            return s
    return {}


def check_video(path: Path, *, vertical: bool, expected_audio_sec: float | None = None) -> list[str]:
    problems = []
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return [f"{path.name}: missing or zero bytes"]

    info = _probe(path)
    v = _video_stream(info)
    a = _audio_stream(info)
    if not v:
        problems.append(f"{path.name}: no video stream")
    if not a:
        problems.append(f"{path.name}: no audio stream")

    w, h = int(v.get("width", 0)), int(v.get("height", 0))
    if vertical and not (w < h):
        problems.append(f"{path.name}: expected 9:16, got {w}x{h}")
    if not vertical and not (w > h):
        problems.append(f"{path.name}: expected 16:9, got {w}x{h}")

    dur = float(info.get("format", {}).get("duration", 0) or 0)
    if dur < 1.0:
        problems.append(f"{path.name}: duration too short ({dur:.2f}s)")
    if expected_audio_sec is not None and dur > 0:
        tolerance = max(3.0, 0.06 * expected_audio_sec)
        if dur + tolerance < expected_audio_sec:
            problems.append(
                f"{path.name}: video {dur:.1f}s much shorter than narration "
                f"{expected_audio_sec:.1f}s (tolerance {tolerance:.1f}s)")
    return problems


def check_outro(path: Path, *, require: bool = True) -> list[str]:
    """Confirm the fixed branded outro was appended as the LAST ~10s, unmodified
    length, and content was not replaced. Uses the render sidecar meta + ffprobe.
    """
    path = Path(path)
    problems = []
    meta_p = Path(str(path) + ".meta.json")
    if not meta_p.exists():
        if require:
            problems.append(f"{path.name}: no render meta -- outro unverified")
        return problems
    try:
        m = json.loads(meta_p.read_text(encoding="utf-8"))
    except Exception:
        if require:
            problems.append(f"{path.name}: unreadable render meta")
        return problems

    outro = float(m.get("outro_sec", 0) or 0)
    content = float(m.get("content_sec", 0) or 0)
    total = float(m.get("total_sec", 0) or 0)

    if require and outro < 9.5:
        problems.append(f"{path.name}: outro missing/short ({outro:.1f}s, need ~10s)")
    if require and total + 0.5 < content + outro:
        problems.append(
            f"{path.name}: outro not appended (total {total:.1f}s < "
            f"content {content:.1f}s + outro {outro:.1f}s)")
    # actual rendered length must match the plan (content + outro)
    info = _probe(path)
    actual = float(info.get("format", {}).get("duration", 0) or 0)
    if actual > 0 and total > 0 and abs(actual - total) > 1.5:
        problems.append(f"{path.name}: length {actual:.1f}s != expected {total:.1f}s")
    return problems


def check_thumbnail(path: Path) -> list[str]:
    problems = []
    try:
        from PIL import Image
        img = Image.open(path)
        if img.size != (C.THUMB_W, C.THUMB_H):
            problems.append(f"thumb: wrong size {img.size}")
        if Path(path).stat().st_size >= 2_000_000:
            problems.append("thumb: over 2MB")
    except Exception as e:  # noqa: BLE001
        problems.append(f"thumb: unreadable ({e})")
    return problems


def run_gate(long_path: Path, shorts: list[dict], thumb: Path,
             narration_sec: float, day_dir: Path) -> bool:
    problems = []
    problems += check_video(long_path, vertical=False, expected_audio_sec=narration_sec)
    for sh in shorts:
        problems += check_video(Path(sh["path"]), vertical=True)
    problems += check_thumbnail(thumb)

    # Outro must be the final ~10s of the LONG video only (NOT Shorts).
    require_outro = Path(C.OUTRO_CLIP).exists()
    problems += check_outro(long_path, require=require_outro)
    if not require_outro:
        log.warning("OUTRO clip not found at %s -- outro NOT enforced this run", C.OUTRO_CLIP)

    report = day_dir / "qa_report.txt"
    passed = len(problems) == 0
    lines = ["QA REPORT", "=" * 40,
             f"long: {long_path}",
             f"shorts: {len(shorts)}",
             f"thumb: {thumb}",
             f"narration_sec: {narration_sec:.1f}",
             f"outro enforced: {require_outro}",
             "",
             "RESULT: " + ("PASS" if passed else "FAIL"),
             ""]
    if problems:
        lines.append("Problems:")
        lines += [f"  - {p}" for p in problems]
    report.write_text("\n".join(lines), encoding="utf-8")
    log.info("QA %s -- report at %s", "PASSED" if passed else "FAILED", report)
    return passed
