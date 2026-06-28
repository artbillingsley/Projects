# src/lib/platforms/youtube.py
from __future__ import annotations

import time
from typing import Any, Dict, Optional

import structlog
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

log = structlog.get_logger()


def get_youtube_client(
    client_id: str, client_secret: str, refresh_token: str
) -> Any:
    credentials = Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri="https://oauth2.googleapis.com/token",
    )
    return build("youtube", "v3", credentials=credentials)


def delete_auto_captions(youtube_client: Any, video_id: str, max_retries: int = 5) -> int:
    """Delete auto-generated (ASR) caption tracks. Returns count deleted.

    YouTube generates ASR captions 3-10 minutes after upload.
    Retry schedule: 60s, 120s, 180s, 240s, 300s (total ~15 min).
    """
    deleted = 0
    for attempt in range(max_retries):
        resp = youtube_client.captions().list(
            part="snippet", videoId=video_id
        ).execute()
        asr_tracks = [
            item for item in resp.get("items", [])
            if item["snippet"].get("trackKind", "").lower() == "asr"
        ]
        if not asr_tracks and attempt < max_retries - 1:
            wait = 60 * (attempt + 1)
            log.info("youtube.captions.waiting", attempt=attempt + 1, wait_s=wait)
            time.sleep(wait)
            continue
        for track in asr_tracks:
            track_id = track["id"]
            youtube_client.captions().delete(id=track_id).execute()
            log.info("youtube.captions.deleted", track_id=track_id, language=track["snippet"].get("language"))
            deleted += 1
        break
    return deleted


def upload_video(
    youtube_client: Any,
    file_path: str,
    title: str,
    description: str,
    tags: list[str],
    category_id: str = "25",
    thumbnail_path: Optional[str] = None,
) -> Dict[str, str]:
    log.info("youtube.upload.start", title=title)

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category_id,
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(file_path, mimetype="video/mp4", resumable=True)
    request = youtube_client.videos().insert(
        part="snippet,status", body=body, media_body=media
    )
    response = request.execute()

    video_id = response["id"]
    video_url = f"https://youtube.com/watch?v={video_id}"

    if thumbnail_path:
        try:
            youtube_client.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path, mimetype="image/png"),
            ).execute()
            log.info("youtube.thumbnail.uploaded", video_id=video_id)
        except Exception as thumb_err:
            log.warning("youtube.thumbnail.failed", video_id=video_id, error=str(thumb_err)[:200])

    deleted = delete_auto_captions(youtube_client, video_id)
    log.info("youtube.upload.done", video_id=video_id, url=video_url, captions_deleted=deleted)
    return {"platform_id": video_id, "platform_url": video_url}
