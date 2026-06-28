# src/lib/platforms/drive.py
from __future__ import annotations

from typing import Any

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

import structlog

log = structlog.get_logger()

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def get_drive_service(sa_key_path: str) -> Any:
    credentials = Credentials.from_service_account_file(sa_key_path, scopes=SCOPES)
    return build("drive", "v3", credentials=credentials)


def create_folder(service: Any, name: str, parent_id: str) -> str:
    body = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    folder = service.files().create(body=body, fields="id").execute()
    return folder["id"]


def upload_file_to_drive(
    service: Any, file_path: str, folder_id: str, file_name: str
) -> str:
    body = {"name": file_name, "parents": [folder_id]}
    media = MediaFileUpload(file_path, resumable=True)
    f = service.files().create(body=body, media_body=media, fields="id").execute()
    log.info("drive.file.uploaded", file=file_name, id=f["id"])
    return f["id"]
