"""utils.py — shared helpers: logging, slugify, json IO, http, subprocess."""
from __future__ import annotations

import json
import logging
import re
import subprocess
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any

import requests

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


log = get_logger("utils")


# ---------------------------------------------------------------------------
# Slug / text
# ---------------------------------------------------------------------------
def slugify(text: str) -> str:
    """`Bermuda Triangle` -> `bermuda_triangle` (ascii, underscores)."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    text = re.sub(r"[\s-]+", "_", text)
    return text or "topic"


# ---------------------------------------------------------------------------
# JSON IO
# ---------------------------------------------------------------------------
def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        log.warning("read_json failed for %s: %s", path, e)
        return default


def write_json(path: Path, data: Any) -> None:
    Path(path).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def extract_json(text: str) -> Any:
    """Pull the first JSON object/array out of an LLM response (handles ```json fences)."""
    if not text:
        raise ValueError("empty text")
    # strip code fences
    text = re.sub(r"^```(?:json)?", "", text.strip())
    text = re.sub(r"```$", "", text.strip()).strip()
    # try direct
    try:
        return json.loads(text)
    except Exception:
        pass
    # find first balanced { } or [ ]
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(text)):
            if text[i] == opener:
                depth += 1
            elif text[i] == closer:
                depth -= 1
                if depth == 0:
                    chunk = text[start : i + 1]
                    try:
                        return json.loads(chunk)
                    except Exception:
                        break
    raise ValueError("no valid JSON found in model output")


# ---------------------------------------------------------------------------
# HTTP with retries
# ---------------------------------------------------------------------------
def http_get(url: str, *, params=None, headers=None, timeout=60, retries=3, stream=False):
    last = None
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(
                url, params=params, headers=headers, timeout=timeout, stream=stream
            )
            if r.status_code == 200:
                return r
            last = f"HTTP {r.status_code}"
            log.warning("GET %s -> %s (try %d/%d)", url[:80], last, attempt, retries)
        except Exception as e:  # noqa: BLE001
            last = str(e)
            log.warning("GET %s failed: %s (try %d/%d)", url[:80], e, attempt, retries)
        time.sleep(2 * attempt)
    raise RuntimeError(f"GET failed after {retries} tries: {last}")


def download(url: str, dest: Path, *, headers=None, timeout=120, retries=3) -> Path:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = http_get(url, headers=headers, timeout=timeout, retries=retries, stream=True)
    with open(dest, "wb") as f:
        for chunk in r.iter_content(chunk_size=1 << 16):
            if chunk:
                f.write(chunk)
    return dest


# ---------------------------------------------------------------------------
# Subprocess (ffmpeg etc.)
# ---------------------------------------------------------------------------
def run(cmd: list[str], *, check=True, quiet=False) -> subprocess.CompletedProcess:
    if not quiet:
        log.info("$ %s", " ".join(str(c) for c in cmd))
    proc = subprocess.run(
        [str(c) for c in cmd], capture_output=True, text=True
    )
    if check and proc.returncode != 0:
        log.error("command failed (%d): %s", proc.returncode, proc.stderr[-800:])
        raise RuntimeError(f"cmd failed: {cmd[0]}")
    return proc


def have(binary: str) -> bool:
    from shutil import which
    return which(binary) is not None
