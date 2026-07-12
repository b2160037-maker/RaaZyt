"""visuals.py -- fetch/generate one visual per scene, matched to narration.

AI images (fail-fast): Pollinations -> Stable Horde (only with a real key)
-> HuggingFace (only with a token) -> Craiyon.
Stock media: Pexels -> Pixabay -> Openverse/Wikimedia.

Rule: prefer real footage for real places, AI for unknowable scenes. Never
leave a blank -- if stock fails, generate an AI image from the narration.
"""
from __future__ import annotations

import time
import urllib.parse
from pathlib import Path

import config as C
from .utils import get_logger, http_get, download
from .fallback import try_chain

log = get_logger("visuals")

# Keywords that suggest a real, photographable place -> prefer stock first.
_REAL_PLACE_HINTS = (
    "pyramid", "temple", "fort", "lake", "mountain", "ocean", "sea", "ship",
    "city", "ruins", "desert", "island", "village", "church", "cave", "river",
)

_ANON_HORDE_KEYS = {"", "0000000000", None}


def _is_real_place(query: str) -> bool:
    q = query.lower()
    return any(h in q for h in _REAL_PLACE_HINTS)


# ---------------------------------------------------------------------------
# AI image providers (all fail FAST -- one quick try, short timeout)
# ---------------------------------------------------------------------------
def _pollinations(prompt: str, out: Path, w: int, h: int) -> Path:
    full = f"{prompt}, {C.IMAGE_STYLE_SUFFIX}"
    url = (
        "https://image.pollinations.ai/prompt/"
        + urllib.parse.quote(full)
        + f"?width={w}&height={h}&nologo=true&seed={int(time.time())%100000}"
    )
    download(url, out.with_suffix(".jpg"), timeout=C.IMAGE_TIMEOUT, retries=C.IMAGE_RETRIES)
    p = out.with_suffix(".jpg")
    if p.stat().st_size < 2000:
        raise RuntimeError("pollinations returned tiny/blank image")
    return p


def _stablehorde(prompt: str, out: Path, w: int, h: int) -> Path:
    import requests
    key = C.STABLEHORDE_KEY
    if key in _ANON_HORDE_KEYS:
        # The anonymous key is rate-limited to 403 in practice -- skip fast.
        raise RuntimeError("no real STABLEHORDE_KEY (anon key is forbidden)")
    payload = {
        "prompt": f"{prompt}, {C.IMAGE_STYLE_SUFFIX}",
        "params": {"width": (w // 64) * 64, "height": (h // 64) * 64, "steps": 25, "n": 1},
        "nsfw": False, "models": ["stable_diffusion"],
    }
    r = requests.post(
        "https://stablehorde.net/api/v2/generate/async",
        headers={"apikey": key, "Content-Type": "application/json"},
        json=payload, timeout=30,
    )
    r.raise_for_status()
    rid = r.json()["id"]
    for _ in range(40):  # poll up to ~3.3 min
        time.sleep(5)
        chk = requests.get(f"https://stablehorde.net/api/v2/generate/check/{rid}", timeout=30).json()
        if chk.get("done"):
            break
    res = requests.get(f"https://stablehorde.net/api/v2/generate/status/{rid}", timeout=60).json()
    gens = res.get("generations", [])
    if not gens:
        raise RuntimeError("stablehorde: no generation")
    download(gens[0]["img"], out.with_suffix(".webp"), timeout=C.IMAGE_TIMEOUT, retries=C.IMAGE_RETRIES)
    return out.with_suffix(".webp")


def _hf_image(prompt: str, out: Path, w: int, h: int) -> Path:
    if not C.HF_TOKEN:
        raise RuntimeError("no HF_TOKEN")
    import requests
    # New HF inference router endpoint (the old api-inference host is deprecated).
    url = f"https://router.huggingface.co/hf-inference/models/{C.HF_IMAGE_MODEL}"
    r = requests.post(
        url,
        headers={"Authorization": f"Bearer {C.HF_TOKEN}"},
        json={"inputs": f"{prompt}, {C.IMAGE_STYLE_SUFFIX}"},
        timeout=C.IMAGE_TIMEOUT,
    )
    if r.status_code != 200 or not r.content or len(r.content) < 2000:
        raise RuntimeError(f"HF image failed: {r.status_code}")
    p = out.with_suffix(".png")
    p.write_bytes(r.content)
    return p


def _craiyon(prompt: str, out: Path, w: int, h: int) -> Path:
    import base64, requests
    r = requests.post(
        "https://api.craiyon.com/v3",
        json={"prompt": f"{prompt}, {C.IMAGE_STYLE_SUFFIX}", "model": "art"},
        timeout=C.IMAGE_TIMEOUT,
    )
    r.raise_for_status()
    imgs = r.json().get("images", [])
    if not imgs:
        raise RuntimeError("craiyon: no images")
    p = out.with_suffix(".webp")
    p.write_bytes(base64.b64decode(imgs[0]))
    return p


def ai_image(prompt: str, out: Path, w: int, h: int) -> Path:
    # Order providers so the ones that actually work are tried FIRST, so we
    # don't waste time on providers that rate-limit / are down.
    providers = []
    if C.HF_TOKEN:
        providers.append(("hf_image", lambda: _hf_image(prompt, out, w, h)))
    providers.append(("pollinations", lambda: _pollinations(prompt, out, w, h)))
    if C.STABLEHORDE_KEY not in _ANON_HORDE_KEYS:
        providers.append(("stablehorde", lambda: _stablehorde(prompt, out, w, h)))
    providers.append(("craiyon", lambda: _craiyon(prompt, out, w, h)))
    return try_chain("ai_image", providers)


# ---------------------------------------------------------------------------
# Stock providers (video preferred, else photo)
# ---------------------------------------------------------------------------
def _pexels(query: str, out: Path, want_video: bool) -> Path:
    if not C.PEXELS_API_KEY:
        raise RuntimeError("no PEXELS_API_KEY")
    headers = {"Authorization": C.PEXELS_API_KEY}
    if want_video:
        r = http_get("https://api.pexels.com/videos/search",
                     params={"query": query, "per_page": 5, "orientation": "landscape"},
                     headers=headers)
        vids = r.json().get("videos", [])
        for v in vids:
            files = sorted(v.get("video_files", []), key=lambda f: f.get("width", 0), reverse=True)
            for f in files:
                if f.get("width", 0) >= 1280:
                    return download(f["link"], out.with_suffix(".mp4"))
        raise RuntimeError("pexels: no suitable video")
    r = http_get("https://api.pexels.com/v1/search",
                 params={"query": query, "per_page": 5}, headers=headers)
    photos = r.json().get("photos", [])
    if not photos:
        raise RuntimeError("pexels: no photos")
    return download(photos[0]["src"]["original"], out.with_suffix(".jpg"))


def _pixabay(query: str, out: Path, want_video: bool) -> Path:
    if not C.PIXABAY_API_KEY:
        raise RuntimeError("no PIXABAY_API_KEY")
    if want_video:
        r = http_get("https://pixabay.com/api/videos/",
                     params={"key": C.PIXABAY_API_KEY, "q": query, "per_page": 5})
        hits = r.json().get("hits", [])
        if hits:
            v = hits[0]["videos"]
            url = (v.get("large") or v.get("medium") or v.get("small"))["url"]
            return download(url, out.with_suffix(".mp4"))
        raise RuntimeError("pixabay: no video")
    r = http_get("https://pixabay.com/api/",
                 params={"key": C.PIXABAY_API_KEY, "q": query, "per_page": 5, "image_type": "photo"})
    hits = r.json().get("hits", [])
    if not hits:
        raise RuntimeError("pixabay: no photo")
    return download(hits[0]["largeImageURL"], out.with_suffix(".jpg"))


def _wikimedia(query: str, out: Path, want_video: bool) -> Path:
    r = http_get("https://commons.wikimedia.org/w/api.php", params={
        "action": "query", "generator": "search", "gsrsearch": f"filetype:bitmap {query}",
        "gsrlimit": 5, "prop": "imageinfo", "iiprop": "url", "iiurlwidth": 1920,
        "format": "json",
    })
    pages = r.json().get("query", {}).get("pages", {})
    for _pid, page in pages.items():
        info = page.get("imageinfo", [{}])[0]
        url = info.get("thumburl") or info.get("url")
        if url:
            return download(url, out.with_suffix(".jpg"))
    raise RuntimeError("wikimedia: nothing found")


def stock_media(query: str, out: Path, want_video: bool = True) -> Path:
    return try_chain(
        "stock",
        [
            ("pexels", lambda: _pexels(query, out, want_video)),
            ("pixabay", lambda: _pixabay(query, out, want_video)),
            ("wikimedia", lambda: _wikimedia(query, out, want_video)),
        ],
    )


# ---------------------------------------------------------------------------
# Public: get one visual for a scene
# ---------------------------------------------------------------------------
def fetch_scene_visual(visual_query: str, mood: str, out_base: Path,
                       w: int = C.LONG_W, h: int = C.LONG_H) -> Path:
    """Return a path to an image or video for this scene. Never blank."""
    out_base = Path(out_base)
    out_base.parent.mkdir(parents=True, exist_ok=True)

    prefer_stock = _is_real_place(visual_query) and mood != "reveal"
    order = ["stock", "ai"] if prefer_stock else ["ai", "stock"]

    for source in order:
        try:
            if source == "stock":
                return stock_media(visual_query, out_base, want_video=False)
            return ai_image(visual_query, out_base, w, h)
        except Exception as e:  # noqa: BLE001
            log.warning("visual source %s failed for %r: %s", source, visual_query[:40], e)

    raise RuntimeError(f"no visual could be produced for {visual_query!r}")
