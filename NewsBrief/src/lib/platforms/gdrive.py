# src/lib/platforms/gdrive.py
"""Upload video + caption markdown to Google Drive via OAuth."""
from __future__ import annotations

import os
from typing import Dict

import structlog
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

log = structlog.get_logger()


def get_drive_client(
    client_id: str, client_secret: str, refresh_token: str,
):
    credentials = Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri="https://oauth2.googleapis.com/token",
    )
    return build("drive", "v3", credentials=credentials)


def upload_to_drive(
    drive_client,
    file_path: str,
    file_name: str,
    folder_id: str,
    mime_type: str = "video/mp4",
) -> Dict[str, str]:
    """Upload a file to a Google Drive folder. Returns file id and webViewLink."""
    log.info("gdrive.upload.start", file_name=file_name)

    file_meta = {
        "name": file_name,
        "parents": [folder_id],
    }
    media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
    result = drive_client.files().create(
        body=file_meta, media_body=media, fields="id, webViewLink",
    ).execute()

    file_id = result["id"]
    link = result.get("webViewLink", "")
    log.info("gdrive.upload.done", file_id=file_id, link=link)
    return {"file_id": file_id, "web_link": link}
