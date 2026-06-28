# src/stages/archive.py
"""Archive video + caption markdown to Google Drive after each pipeline run."""
from __future__ import annotations

import os
import tempfile
from typing import Any, Dict, Optional

import structlog

from src.lib.captions import build_caption
from src.lib.platforms.gdrive import get_drive_client, upload_to_drive

log = structlog.get_logger()


def _build_markdown(spec: Dict, youtube_url: str = "") -> str:
    """Build a markdown file with all platform captions."""
    date = spec.get("date", "")
    ig_caption = build_caption(spec, platform="instagram")
    fb_caption = build_caption(spec, platform="facebook", youtube_url=youtube_url)
    li_caption = build_caption(spec, platform="linkedin", youtube_url=youtube_url)

    # Threads caption (short form with link)
    headlines = []
    for slot in spec.get("slots", []):
        if slot.get("type") == "LEAD":
            headlines.append(slot.get("headline", slot.get("copy", "")[:80]))
    lead = headlines[0] if headlines else ""
    scan_count = 0
    for slot in spec.get("slots", []):
        if slot.get("type") == "SCAN":
            scan_count = len(slot.get("items", []))
    threads_parts = [
        f"COGNOSCERE Daily Brief \u2014 {date}",
        "",
        lead,
    ]
    if scan_count:
        threads_parts.append(f"+ {scan_count} more stories")
    threads_parts.append("")
    if youtube_url:
        threads_parts.append(f"Watch: {youtube_url}")
        threads_parts.append("")
    threads_parts.append("Decide.")
    threads_caption = "\n".join(threads_parts)

    return f"""# COGNOSCERE Daily Brief — {date}

## Instagram Caption (no links)

{ig_caption}

---

## Facebook Reel Caption

{fb_caption}

---

## LinkedIn Caption

{li_caption}

---

## Threads Caption

{threads_caption}
"""


def archive_to_drive(
    config: Any,
    spec: Dict,
    video_path: str,
    date_str: str,
    youtube_url: str = "",
) -> Optional[Dict[str, str]]:
    """Upload video + markdown to Google Drive /NewsBrief/ folder."""
    folder_id = getattr(config, "gdrive_folder_id", "")
    refresh_token = getattr(config, "gdrive_refresh_token", "")
    client_id = getattr(config, "gdrive_client_id", "")
    client_secret = getattr(config, "gdrive_client_secret", "")

    if not all([folder_id, refresh_token, client_id, client_secret]):
        log.warning("archive.skipped", reason="Google Drive not configured")
        return None

    client = get_drive_client(client_id, client_secret, refresh_token)

    # Upload video
    video_name = f"{date_str}.mp4"
    video_result = upload_to_drive(
        client, video_path, video_name, folder_id, mime_type="video/mp4",
    )

    # Build and upload markdown
    md_content = _build_markdown(spec, youtube_url=youtube_url)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(md_content)
        md_path = f.name

    try:
        md_name = f"{date_str}.md"
        md_result = upload_to_drive(
            client, md_path, md_name, folder_id, mime_type="text/markdown",
        )
    finally:
        os.unlink(md_path)

    log.info("archive.complete",
             video_link=video_result["web_link"],
             md_link=md_result["web_link"])

    return {
        "video_link": video_result["web_link"],
        "md_link": md_result["web_link"],
    }
