# src/lib/platforms/instagram.py
from __future__ import annotations

import os
import time
from typing import Dict

import requests
import structlog

log = structlog.get_logger()

GRAPH_API = "https://graph.facebook.com/v25.0"

# Base URL for serving video files via nginx for Instagram hosted-URL upload.
# The nginx location /tmp-video/ aliases to the newsbrief tmp/ directory.
IG_VIDEO_BASE_URL = os.environ.get(
    "IG_VIDEO_BASE_URL", "https://cifaas.cognoscerellc.com/tmp-video"
)


def upload_reel(
    ig_account_id: str,
    access_token: str,
    file_path: str,
    caption: str,
    max_poll_seconds: int = 300,
) -> Dict[str, str]:
    """Upload a Reel to Instagram via hosted video URL.

    The video must be served over HTTPS at a publicly accessible URL.
    We use the nginx /tmp-video/ location on cifaas.cognoscerellc.com
    which maps to the newsbrief tmp/ directory.
    """
    file_size = os.path.getsize(file_path)
    log.info("instagram.reel.upload.start", file_size=file_size)

    # Build public URL from the file path
    # file_path looks like: /home/ec2-user/newsbrief/tmp/2026-07-03/anchor-9x16.mp4
    # We need the part after /tmp/: 2026-07-03/anchor-9x16.mp4
    tmp_idx = file_path.find("/tmp/")
    if tmp_idx >= 0:
        relative = file_path[tmp_idx + 5:]  # skip "/tmp/"
    else:
        relative = os.path.basename(file_path)
    video_url = "%s/%s" % (IG_VIDEO_BASE_URL.rstrip("/"), relative)
    log.info("instagram.video_url", url=video_url)

    # Step 1: Create container with video_url (hosted method)
    resp = requests.post(
        "%s/%s/media" % (GRAPH_API, ig_account_id),
        data={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "access_token": access_token,
        },
        timeout=60,
    )
    resp.raise_for_status()
    container_id = resp.json()["id"]
    log.info("instagram.container.created", container_id=container_id)

    # Step 2: Poll until ready
    start = time.monotonic()
    while time.monotonic() - start < max_poll_seconds:
        status_resp = requests.get(
            "%s/%s" % (GRAPH_API, container_id),
            params={"fields": "status_code,status", "access_token": access_token},
            timeout=30,
        )
        status_resp.raise_for_status()
        data = status_resp.json()
        status_code = data.get("status_code", "")

        if status_code == "FINISHED":
            break
        elif status_code == "ERROR":
            error_msg = data.get("status", "unknown error")
            raise RuntimeError(
                "Instagram container %s failed: %s" % (container_id, error_msg)
            )

        log.info("instagram.polling", status=status_code)
        time.sleep(10)
    else:
        raise TimeoutError(
            "Instagram container %s stuck after %ds" % (container_id, max_poll_seconds)
        )

    # Step 3: Publish
    pub_resp = requests.post(
        "%s/%s/media_publish" % (GRAPH_API, ig_account_id),
        data={"creation_id": container_id, "access_token": access_token},
        timeout=60,
    )
    pub_resp.raise_for_status()
    media_id = pub_resp.json().get("id", "")

    log.info("instagram.reel.upload.done", media_id=media_id)
    return {"platform_id": media_id, "platform_url": "https://instagram.com/reel/%s" % media_id}
