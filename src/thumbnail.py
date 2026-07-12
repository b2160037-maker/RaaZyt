"""thumbnail.py -- owner-drop with auto-fallback (File 1 Section 9).

1. Pull the shared Drive folder (rclone) into thumbnails/.
2. Look for <slug>.png / .jpg matching today's slug -> use it.
3. Else auto-generate (Pollinations -> Horde -> HF) + optional Hinglish overlay.
Always returns a valid 1280x720 file (JPEG, < 2MB), never blocks upload.
"""
from __future__ import annotations

from pathlib import Path

import config as C
from .utils import get_logger, run, have
from . import visuals

log = get_logger("thumbnail")

AUTO_PROMPT = (
    "Create a hyper-dramatic cinematic YouTube thumbnail, 1280x720, about {TOPIC}. "
    "Dark moody atmosphere with one intense glowing focal point (mysterious light, "
    "glowing eyes, storm vortex). Ultra-high contrast, deep blacks with electric "
    "teal/orange rim lighting. A young man shocked reaction face OR silhouette in the "
    "corner for emotional pull. Leave clean empty space on the left third for bold text. "
    "Photorealistic, 8K detail, dramatic fog, volumetric god rays. NO text in the image. "
    "Composition must trigger instant curiosity."
)


def _pull_drive():
    if not (C.RCLONE_CONF and have("rclone")):
        return
    try:
        run(["rclone", "copy", C.RCLONE_REMOTE, str(C.THUMBS_DIR)], check=False)
    except Exception as e:  # noqa: BLE001
        log.warning("rclone pull failed (non-fatal): %s", e)


def _find_owner_drop(slug: str, date: str | None = None) -> Path | None:
    names = [slug] + ([date] if date else [])
    for base in names:
        for ext in (".png", ".jpg", ".jpeg", ".webp"):
            p = C.THUMBS_DIR / f"{base}{ext}"
            if p.exists() and p.stat().st_size > 5000:
                return p
    return None


def _save_under_2mb(img, dst: Path) -> Path:
    """Save as JPEG, stepping quality down until the file is safely < 2MB
    (YouTube's thumbnail limit). PNG photos routinely exceed 2MB; JPEG does not."""
    dst = dst.with_suffix(".jpg")
    for q in (90, 85, 80, 72, 65, 55):
        img.save(dst, "JPEG", quality=q, optimize=True)
        if dst.stat().st_size < 1_950_000:
            break
    return dst


def _fit_1280x720(src: Path, dst: Path) -> Path:
    from PIL import Image
    img = Image.open(src).convert("RGB").resize((C.THUMB_W, C.THUMB_H))
    return _save_under_2mb(img, dst)


def _overlay_text(img_path: Path, text: str) -> Path:
    """Bold Hinglish hook in the clean left third."""
    from PIL import Image, ImageDraw, ImageFont
    img = Image.open(img_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    font = None
    for cand in (C.FONTS_DIR / "Anton-Regular.ttf",
                 C.FONTS_DIR / "BebasNeue-Regular.ttf",
                 Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")):
        if Path(cand).exists():
            try:
                font = ImageFont.truetype(str(cand), 110)
                break
            except Exception:
                continue
    if font is None:
        font = ImageFont.load_default()

    x, y = 40, 210
    for dx in (-3, 0, 3):
        for dy in (-3, 0, 3):
            draw.text((x + dx, y + dy), text, font=font, fill=(0, 0, 0))
    draw.text((x, y), text, font=font, fill=(255, 220, 40))
    return _save_under_2mb(img, img_path)


def _validate(path: Path) -> bool:
    try:
        from PIL import Image
        img = Image.open(path)
        return img.size == (C.THUMB_W, C.THUMB_H) and path.stat().st_size < 2_000_000
    except Exception:
        return False


def get_thumbnail(topic: str, slug: str, out_dir: Path, hook_text: str = "",
                  date: str | None = None) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    final = out_dir / "thumb.jpg"

    _pull_drive()
    owner = _find_owner_drop(slug, date)
    if owner:
        log.info("Using owner-dropped thumbnail: %s", owner.name)
        out = _fit_1280x720(owner, final)
        if _validate(out):
            return out

    log.info("No owner thumbnail -- auto-generating.")
    raw = out_dir / "thumb_raw"
    gen = visuals.ai_image(AUTO_PROMPT.format(TOPIC=topic), raw, C.THUMB_W, C.THUMB_H)
    out = _fit_1280x720(gen, final)
    if hook_text:
        try:
            out = _overlay_text(out, hook_text.upper()[:18])
        except Exception as e:  # noqa: BLE001
            log.warning("overlay failed (non-fatal): %s", e)

    if not _validate(out):
        out = _template_card(topic, out)
    return out


def _template_card(topic: str, dst: Path) -> Path:
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (C.THUMB_W, C.THUMB_H), (8, 10, 14))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 90)
    except Exception:
        font = ImageFont.load_default()
    draw.text((60, 300), topic[:26], font=font, fill=(255, 210, 40))
    return _save_under_2mb(img, dst)
