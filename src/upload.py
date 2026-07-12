"""upload.py -- safe YouTube upload (Data API v3, File 2 Section 6).

Resumable upload, exponential-backoff retries, thumbnail set, optional pinned
comment + playlist. Auth from YT_CLIENT_SECRET_JSON + YT_TOKEN_JSON secrets;
token auto-refreshes (no re-login).
"""
from __future__ import annotations

import json
import random
import time
from pathlib import Path

import config as C
from .utils import get_logger

log = get_logger("upload")

# Scopes used ONLY when minting a fresh token in get_token.py. We deliberately
# do NOT force these when refreshing a stored token (see _service): forcing a
# scope set that differs from what the token was actually granted makes Google's
# refresh endpoint return 'invalid_scope'. The stored token already carries its
# granted scopes, so we let it refresh with those.
SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.force-ssl"]


def _service():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    if not C.YT_TOKEN_JSON:
        raise RuntimeError("YT_TOKEN_JSON secret missing -- run get_token.py once")
    try:
        info = json.loads(C.YT_TOKEN_JSON)
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"YT_TOKEN_JSON is not valid JSON: {e}")

    # Load using the token's OWN granted scopes (info['scopes']); do not override.
    creds = Credentials.from_authorized_user_info(info)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:  # noqa: BLE001
                raise RuntimeError(
                    "YouTube token refresh failed (" + str(e) + "). Re-run "
                    "get_token.py to mint a fresh token.json and update the "
                    "YT_TOKEN_JSON secret. Also make sure your Google account is "
                    "a Test user on the OAuth consent screen."
                )
        else:
            raise RuntimeError("YouTube creds invalid and cannot refresh -- re-run get_token.py")
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def _resumable_insert(youtube, path: Path, body: dict) -> str:
    from googleapiclient.http import MediaFileUpload
    media = MediaFileUpload(str(path), chunksize=-1, resumable=True)
    request = youtube.videos().insert(
        part="snippet,status", body=body, media_body=media
    )
    response = None
    backoff = 2
    tries = 0
    while response is None:
        try:
            status, response = request.next_chunk()
        except Exception as e:  # noqa: BLE001 (retry 5xx/quota)
            tries += 1
            if tries > 3:
                raise
            sleep = backoff * (2 ** (tries - 1)) + random.random()
            log.warning("upload chunk error (%s) -- retry %d in %.1fs", e, tries, sleep)
            time.sleep(sleep)
    return response["id"]


def upload_video(path: Path, meta: dict, *, publish_at: str | None = None) -> dict:
    youtube = _service()
    status = {"privacyStatus": meta.get("privacyStatus", C.YT_PRIVACY),
              "selfDeclaredMadeForKids": bool(meta.get("madeForKids", False))}
    if publish_at:
        status["privacyStatus"] = "private"
        status["publishAt"] = publish_at
    body = {
        "snippet": {
            "title": meta["title"],
            "description": meta["description"],
            "tags": meta.get("tags", []),
            "categoryId": meta.get("categoryId", C.YT_CATEGORY_ID),
            "defaultLanguage": meta.get("defaultLanguage", "hi"),
            "defaultAudioLanguage": "hi",
        },
        "status": status,
    }
    vid = _resumable_insert(youtube, path, body)
    url = f"https://www.youtube.com/watch?v={vid}"
    log.info("uploaded %s -> %s", Path(path).name, url)
    return {"id": vid, "url": url}


def set_thumbnail(video_id: str, thumb: Path) -> None:
    try:
        youtube = _service()
        from googleapiclient.http import MediaFileUpload
        youtube.thumbnails().set(
            videoId=video_id, media_body=MediaFileUpload(str(thumb))
        ).execute()
        log.info("thumbnail set for %s", video_id)
    except Exception as e:  # noqa: BLE001
        log.warning("set_thumbnail failed (non-fatal): %s", e)


def pin_comment(video_id: str, text: str) -> None:
    try:
        youtube = _service()
        youtube.commentThreads().insert(
            part="snippet",
            body={"snippet": {"videoId": video_id,
                              "topLevelComment": {"snippet": {"textOriginal": text}}}},
        ).execute()
        log.info("posted first comment on %s", video_id)
    except Exception as e:  # noqa: BLE001
        log.warning("pin_comment failed (non-fatal): %s", e)


def add_to_playlist(video_id: str, playlist_title: str) -> None:
    """Find-or-create a playlist by title, then add the video."""
    try:
        youtube = _service()
        pid = None
        res = youtube.playlists().list(part="snippet", mine=True, maxResults=50).execute()
        for it in res.get("items", []):
            if it["snippet"]["title"].lower() == playlist_title.lower():
                pid = it["id"]
                break
        if not pid:
            created = youtube.playlists().insert(
                part="snippet,status",
                body={"snippet": {"title": playlist_title},
                      "status": {"privacyStatus": "public"}},
            ).execute()
            pid = created["id"]
        youtube.playlistItems().insert(
            part="snippet",
            body={"snippet": {"playlistId": pid,
                              "resourceId": {"kind": "youtube#video", "videoId": video_id}}},
        ).execute()
        log.info("added %s to playlist '%s'", video_id, playlist_title)
    except Exception as e:  # noqa: BLE001
        log.warning("add_to_playlist failed (non-fatal): %s", e)


def upload_caption(video_id: str, srt_path, language: str = "hi",
                   name: str = "RAAZ FILES") -> None:
    """Upload an SRT caption track (viewer-off, indexed by YouTube for search)."""
    try:
        from pathlib import Path
        if not Path(srt_path).exists() or Path(srt_path).stat().st_size == 0:
            return
        youtube = _service()
        from googleapiclient.http import MediaFileUpload
        youtube.captions().insert(
            part="snippet",
            body={"snippet": {"videoId": video_id, "language": language,
                              "name": name, "isDraft": False}},
            media_body=MediaFileUpload(str(srt_path)),
        ).execute()
        log.info("caption (SRT) uploaded for %s", video_id)
    except Exception as e:  # noqa: BLE001
        log.warning("caption upload failed (non-fatal): %s", e)
