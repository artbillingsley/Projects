# src/lib/platforms/instagram.py
from __future__ import annotations

import os
import time
from typing import Dict

import requests
import structlog

log = structlog.get_logger()

GRAPH_API = "https://graph.facebook.com/v25.0"


def upload_reel(
    ig_account_id: str,
    access_token: str,
    file_path: str,
    caption: str,
    max_poll_seconds: int = 300,
) -> Dict[str, str]:
    """Upload a Reel to Instagram via resumable direct upload."""
    file_size = os.path.getsize(file_path)
    log.info("instagram.reel.upload.start", file_size=file_size)

    # Step 1: Create container with resumable upload type
    resp = requests.post(
        f"{GRAPH_API}/{ig_account_id}/media",
        data={
            "media_type": "REELS",
            "upload_type": "resumable",
            "caption": caption,
            "access_token": access_token,
        },
        timeout=60,
    )
    resp.raise_for_status()
    resp_data = resp.json()
    container_id = resp_data["id"]
    upload_uri = resp_data["uri"]
    log.info("instagram.container.created", container_id=container_id, upload_uri=upload_uri)

    # Step 2: PUT binary to the URI returned by container creation
    with open(file_path, "rb") as f:
        put_resp = requests.put(
            upload_uri,
            data=f,
            headers={
                "Authorization": f"OAuth {access_token}",
                "offset": "0",
                "file_size": str(file_size),
                "Content-Type": "application/octet-stream",
            },
            timeout=300,
        )
    put_resp.raise_for_status()
    log.info("instagram.binary.uploaded", container_id=container_id)

    # Step 3: Poll until ready
    start = time.monotonic()
    while time.monotonic() - start < max_poll_seconds:
        status_resp = requests.get(
            f"{GRAPH_API}/{container_id}",
            params={"fields": "status_code", "access_token": access_token},
            timeout=30,
        )
        status_resp.raise_for_status()
        status_code = status_resp.json().get("status_code", "")

        if status_code == "FINISHED":
            break
        elif status_code == "ERROR":
            raise RuntimeError(f"Instagram container {container_id} failed processing")

        log.info("instagram.polling", status=status_code)
        time.sleep(10)
    else:
        raise TimeoutError(
            f"Instagram container {container_id} stuck after {max_poll_seconds}s"
        )

    # Step 4: Publish
    pub_resp = requests.post(
        f"{GRAPH_API}/{ig_account_id}/media_publish",
        data={"creation_id": container_id, "access_token": access_token},
        timeout=60,
    )
    pub_resp.raise_for_status()
    media_id = pub_resp.json().get("id", "")

    log.info("instagram.reel.upload.done", media_id=media_id)
    return {"platform_id": media_id, "platform_url": f"https://instagram.com/reel/{media_id}"}
