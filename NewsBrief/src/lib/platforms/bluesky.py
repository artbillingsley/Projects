# src/lib/platforms/bluesky.py
"""Upload video + post to Bluesky via AT Protocol."""
from __future__ import annotations

from typing import Dict

import structlog

log = structlog.get_logger()


def upload_video_post(
    handle: str,
    app_password: str,
    file_path: str,
    caption: str,
) -> Dict[str, str]:
    """Upload a video and create a post on Bluesky."""
    from atproto import Client

    log.info("bluesky.post.start", handle=handle)

    client = Client()
    client.login(handle, app_password)

    # Upload video blob
    with open(file_path, "rb") as f:
        video_data = f.read()

    log.info("bluesky.upload.start", size=len(video_data))
    video_blob = client.upload_blob(video_data)

    # Create post with video embed
    from atproto import models

    embed = models.AppBskyEmbedVideo.Main(
        video=video_blob.blob,
    )

    post = client.send_post(
        text=caption[:300],
        embed=embed,
    )

    post_uri = post.uri
    # Convert AT URI to web URL: at://did:plc:xxx/app.bsky.feed.post/yyy -> bsky.app/profile/handle/post/yyy
    rkey = post_uri.split("/")[-1]
    post_url = f"https://bsky.app/profile/{handle}/post/{rkey}"

    log.info("bluesky.post.done", uri=post_uri, url=post_url)
    return {"platform_id": post_uri, "platform_url": post_url}
