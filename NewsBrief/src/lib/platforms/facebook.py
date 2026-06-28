# src/lib/platforms/facebook.py
from __future__ import annotations

import os
from typing import Dict

import requests
import structlog

log = structlog.get_logger()

GRAPH_API = "https://graph.facebook.com/v25.0"


def upload_video(
    page_id: str,
    access_token: str,
    file_path: str,
    description: str,
) -> Dict[str, str]:
    log.info("facebook.video.upload.start")

    with open(file_path, "rb") as f:
        resp = requests.post(
            f"{GRAPH_API}/{page_id}/videos",
            files={"source": f},
            data={"description": description, "access_token": access_token},
            timeout=300,
        )

    resp.raise_for_status()
    data = resp.json()
    post_id = data.get("id", "")

    log.info("facebook.video.upload.done", post_id=post_id)
    return {"platform_id": post_id, "platform_url": f"https://facebook.com/{post_id}"}


def upload_reel(
    page_id: str,
    access_token: str,
    file_path: str,
    description: str,
) -> Dict[str, str]:
    """Upload a Reel to Facebook via direct /videos upload.

    Facebook auto-detects 9:16 vertical videos as Reels.
    The 3-phase /video_reels endpoint creates drafts that don't publish.
    """
    log.info("facebook.reel.upload.start")

    with open(file_path, "rb") as f:
        resp = requests.post(
            f"{GRAPH_API}/{page_id}/videos",
            files={"source": f},
            data={
                "description": description,
                "published": "true",
                "access_token": access_token,
            },
            timeout=300,
        )

    resp.raise_for_status()
    data = resp.json()
    post_id = data.get("id", "")

    log.info("facebook.reel.upload.done", post_id=post_id)
    return {"platform_id": post_id, "platform_url": f"https://facebook.com/reel/{post_id}"}


def post_comment(
    post_id: str,
    access_token: str,
    message: str,
) -> str:
    """Post a comment on a Facebook video/reel. Returns comment ID."""
    resp = requests.post(
        f"{GRAPH_API}/{post_id}/comments",
        data={"message": message, "access_token": access_token},
        timeout=30,
    )
    resp.raise_for_status()
    comment_id = resp.json().get("id", "")
    log.info("facebook.comment.posted", post_id=post_id, comment_id=comment_id)
    return comment_id
