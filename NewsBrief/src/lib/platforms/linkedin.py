# src/lib/platforms/linkedin.py
from __future__ import annotations

from typing import Dict, Optional

import requests
import structlog

log = structlog.get_logger()

API_BASE = "https://api.linkedin.com/v2"


def upload_video(
    access_token: str,
    file_path: str,
    caption: str,
    title: str,
    member_id: str = "",
    org_id: str = "",
) -> Dict[str, str]:
    """Upload video to LinkedIn as a person or organization."""
    if member_id:
        author_urn = f"urn:li:person:{member_id}"
    elif org_id:
        author_urn = f"urn:li:organization:{org_id}"
    else:
        raise ValueError("Either member_id or org_id is required")

    headers = {"Authorization": f"Bearer {access_token}"}
    log.info("linkedin.upload.start", author=author_urn)

    # Step 1: Register upload
    register_resp = requests.post(
        f"{API_BASE}/assets?action=registerUpload",
        headers=headers,
        json={
            "registerUploadRequest": {
                "owner": author_urn,
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-video"],
                "serviceRelationships": [{
                    "identifier": "urn:li:userGeneratedContent",
                    "relationshipType": "OWNER",
                }],
            }
        },
        timeout=60,
    )
    register_resp.raise_for_status()
    upload_data = register_resp.json()["value"]
    upload_url = upload_data["uploadMechanism"][
        "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
    ]["uploadUrl"]
    asset_urn = upload_data["asset"]

    # Step 2: PUT binary
    log.info("linkedin.upload.binary", asset=asset_urn)
    with open(file_path, "rb") as f:
        put_resp = requests.put(
            upload_url,
            data=f,
            headers={**headers, "Content-Type": "application/octet-stream"},
            timeout=300,
        )
    put_resp.raise_for_status()

    # Step 3: Create post
    post_resp = requests.post(
        f"{API_BASE}/ugcPosts",
        headers=headers,
        json={
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": caption},
                    "shareMediaCategory": "VIDEO",
                    "media": [{
                        "status": "READY",
                        "media": asset_urn,
                        "title": {"text": title},
                    }],
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        },
        timeout=60,
    )
    post_resp.raise_for_status()
    # URN may be in header or response body
    post_urn = post_resp.headers.get("X-RestLi-Id", "")
    if not post_urn:
        body = post_resp.json() if post_resp.text else {}
        post_urn = body.get("id", "")

    log.info("linkedin.upload.done", post_urn=post_urn)
    return {"platform_id": post_urn, "platform_url": f"https://linkedin.com/feed/update/{post_urn}"}
