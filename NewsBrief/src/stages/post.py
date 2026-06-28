# src/stages/post.py
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import structlog

log = structlog.get_logger()


@dataclass
class UploadResult:
    platform: str
    status: str  # "completed" | "failed" | "skipped"
    platform_id: str = ""
    platform_url: str = ""
    error_message: str = ""
    file_name: str = ""
    aspect_ratio: str = ""
    content_type: str = ""
    clip_id: str = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_clip_file(output_dir: str, clip_id: str) -> Optional[str]:
    """Return the first file in output_dir whose name contains clip_id, or None."""
    if not os.path.isdir(output_dir):
        return None
    for fname in sorted(os.listdir(output_dir)):
        if clip_id in fname and fname.endswith(".mp4"):
            return os.path.join(output_dir, fname)
    return None


def _find_best_clip(output_dir: str) -> Optional[str]:
    """Return the best (default C1) clip file from output_dir."""
    result = _find_clip_file(output_dir, "C1")
    if result:
        return result
    # Fall back to first .mp4 found
    if os.path.isdir(output_dir):
        for fname in sorted(os.listdir(output_dir)):
            if fname.endswith(".mp4"):
                return os.path.join(output_dir, fname)
    return None


def _find_short_clip(output_dir: str) -> Optional[str]:
    """Return the vertical/short clip (C2 or 9x16)."""
    result = _find_clip_file(output_dir, "C2")
    if result:
        return result
    for fname in sorted(os.listdir(output_dir) if os.path.isdir(output_dir) else []):
        if ("9x16" in fname or "short" in fname.lower()) and fname.endswith(".mp4"):
            return os.path.join(output_dir, fname)
    return _find_best_clip(output_dir)


# ---------------------------------------------------------------------------
# Private upload functions (lazy-import platform clients inside each)
# ---------------------------------------------------------------------------

def _brief_label(spec: Dict) -> str:
    """Return 'Tech Brief' or 'Daily Brief' based on spec brief_id."""
    bid = spec.get("brief_id", "")
    return "Tech Brief" if bid.startswith("tech-") else "Daily Brief"


def _is_tech_brief(spec: Dict) -> bool:
    return spec.get("brief_id", "").startswith("tech-")


def _find_thumbnail(output_dir: str, spec: Dict) -> str:
    """Find the branded thumbnail for this brief type."""
    import os
    assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "assets")
    thumb = "thumb_tech.png" if _is_tech_brief(spec) else "thumb_news.png"
    path = os.path.join(assets_dir, thumb)
    # Also check output_dir for a copied thumbnail
    out_path = os.path.join(output_dir, "thumbnail.png")
    if os.path.exists(out_path):
        return out_path
    return path if os.path.exists(path) else ""


def _upload_youtube_video(output_dir: str, spec: Dict, config: Any) -> Dict[str, str]:
    from src.lib.platforms.youtube import get_youtube_client, upload_video
    from src.lib.captions import build_caption

    client = get_youtube_client(
        client_id=getattr(config, "youtube_client_id", ""),
        client_secret=getattr(config, "youtube_client_secret", ""),
        refresh_token=getattr(config, "youtube_refresh_token", ""),
    )
    file_path = _find_short_clip(output_dir) or ""
    date = spec.get("date", "")
    label = _brief_label(spec)
    thumbnail = _find_thumbnail(output_dir, spec)
    description = build_caption(spec, platform="youtube")
    return upload_video(
        youtube_client=client,
        file_path=file_path,
        title=f"COGNOSCERE {label} \u2014 {date} #Shorts",
        description=description,
        tags=["COGNOSCERE", label.replace(" ", ""), "Shorts"],
        thumbnail_path=thumbnail if thumbnail else None,
    )


def _upload_youtube_short(output_dir: str, spec: Dict, config: Any) -> Dict[str, str]:
    from src.lib.platforms.youtube import get_youtube_client, upload_video
    from src.lib.captions import build_caption

    client = get_youtube_client(
        client_id=getattr(config, "youtube_client_id", ""),
        client_secret=getattr(config, "youtube_client_secret", ""),
        refresh_token=getattr(config, "youtube_refresh_token", ""),
    )
    file_path = _find_short_clip(output_dir) or ""
    date = spec.get("date", "")
    label = _brief_label(spec)
    thumbnail = _find_thumbnail(output_dir, spec)
    description = build_caption(spec, platform="youtube")
    return upload_video(
        youtube_client=client,
        file_path=file_path,
        title=f"COGNOSCERE {label} \u2014 {date} #Shorts",
        description=description,
        tags=["COGNOSCERE", label.replace(" ", ""), "Shorts"],
        thumbnail_path=thumbnail if thumbnail else None,
    )



def _upload_youtube_short_2(output_dir: str, spec: Dict, config: Any) -> Dict[str, str]:
    from src.lib.platforms.youtube import get_youtube_client, upload_video
    from src.lib.captions import build_caption

    client = get_youtube_client(
        client_id=getattr(config, "youtube2_client_id", ""),
        client_secret=getattr(config, "youtube2_client_secret", ""),
        refresh_token=getattr(config, "youtube2_refresh_token", ""),
    )
    file_path = _find_short_clip(output_dir) or ""
    date = spec.get("date", "")
    label = _brief_label(spec)
    thumbnail = _find_thumbnail(output_dir, spec)
    description = build_caption(spec, platform="youtube")
    return upload_video(
        youtube_client=client,
        file_path=file_path,
        title=f"COGNOSCERE {label} \u2014 {date} #Shorts",
        description=description,
        tags=["COGNOSCERE", label.replace(" ", ""), "Shorts"],
        thumbnail_path=thumbnail if thumbnail else None,
    )


def _upload_youtube_short_3(output_dir: str, spec: Dict, config: Any) -> Dict[str, str]:
    from src.lib.platforms.youtube import get_youtube_client, upload_video
    from src.lib.captions import build_caption

    client = get_youtube_client(
        client_id=getattr(config, "youtube3_client_id", ""),
        client_secret=getattr(config, "youtube3_client_secret", ""),
        refresh_token=getattr(config, "youtube3_refresh_token", ""),
    )
    file_path = _find_short_clip(output_dir) or ""
    date = spec.get("date", "")
    label = _brief_label(spec)
    thumbnail = _find_thumbnail(output_dir, spec)
    description = build_caption(spec, platform="youtube")
    return upload_video(
        youtube_client=client,
        file_path=file_path,
        title=f"COGNOSCERE {label} \u2014 {date} #Shorts",
        description=description,
        tags=["COGNOSCERE", label.replace(" ", ""), "Shorts"],
        thumbnail_path=thumbnail if thumbnail else None,
    )


def _upload_facebook_reel(output_dir: str, spec: Dict, config: Any, youtube_url: str = "") -> Dict[str, str]:
    from src.lib.platforms.facebook import upload_reel, post_comment
    from src.lib.captions import build_caption, _extract_headlines

    file_path = _find_short_clip(output_dir) or ""
    caption = build_caption(spec, platform="facebook", youtube_url=youtube_url)
    result = upload_reel(
        page_id=getattr(config, "facebook_page_id", ""),
        access_token=getattr(config, "facebook_access_token", ""),
        file_path=file_path,
        description=caption,
    )

    # Post headlines as a visible comment (Reels hide description behind "See more")
    headlines = _extract_headlines(spec)
    if headlines and result.get("platform_id"):
        label = _brief_label(spec)
        date = spec.get("date", "")
        bullet_lines = "\n".join(f"\u25b6 {h}" for h in headlines)
        comment = f"COGNOSCERE {label} \u2014 {date}\n\n{bullet_lines}"
        if youtube_url:
            comment += f"\n\n\u25b6 Watch on YouTube Shorts: {youtube_url}"
        try:
            post_comment(
                post_id=result["platform_id"],
                access_token=getattr(config, "facebook_access_token", ""),
                message=comment,
            )
        except Exception as e:
            log.warning("facebook.comment.failed", error=str(e))

    return result


def _upload_instagram_reel(output_dir: str, spec: Dict, config: Any) -> Dict[str, str]:
    from src.lib.platforms.instagram import upload_reel
    from src.lib.captions import build_caption

    file_path = _find_short_clip(output_dir) or ""
    caption = build_caption(spec, platform="instagram")
    return upload_reel(
        ig_account_id=getattr(config, "instagram_account_id", ""),
        access_token=getattr(config, "facebook_access_token", ""),
        file_path=file_path,
        caption=caption,
    )


def _upload_linkedin_video(
    output_dir: str, spec: Dict, config: Any, youtube_url: str = "",
) -> Dict[str, str]:
    from src.lib.platforms.linkedin import upload_video
    from src.lib.captions import build_caption

    file_path = _find_short_clip(output_dir) or ""
    date = spec.get("date", "")
    member_id = getattr(config, "linkedin_member_id", "")
    org_id = getattr(config, "linkedin_org_id", "")
    caption = build_caption(spec, platform="linkedin", youtube_url=youtube_url)
    return upload_video(
        access_token=getattr(config, "linkedin_access_token", ""),
        file_path=file_path,
        caption=caption,
        title=f"COGNOSCERE Daily Brief \u2014 {date}",
        member_id=member_id,
        org_id=org_id if not member_id else "",
    )


def _upload_bluesky_post(output_dir: str, spec: Dict, config: Any, youtube_url: str = "") -> Dict[str, str]:
    from src.lib.platforms.bluesky import upload_video_post
    from src.lib.captions import build_caption

    file_path = _find_short_clip(output_dir) or ""
    caption = build_caption(spec, platform="bluesky", youtube_url=youtube_url)
    return upload_video_post(
        handle=getattr(config, "bluesky_handle", ""),
        app_password=getattr(config, "bluesky_app_password", ""),
        file_path=file_path,
        caption=caption,
    )


# ---------------------------------------------------------------------------
# Upload dispatch table
# (platform_name, fn_name, file_name, aspect_ratio, content_type)
#
# Store function *names* (strings) rather than direct references so that
# unittest.mock.patch can intercept the module-level attribute at call time.
# ---------------------------------------------------------------------------

_UPLOAD_FNS = [
    ("youtube_video",    "_upload_youtube_video",    "9x16.mp4",  "9:16",  "video"),
    ("youtube_short",    "_upload_youtube_short",    "9x16.mp4",  "9:16",  "short"),
    ("youtube_short_2",  "_upload_youtube_short_2",  "9x16.mp4",  "9:16",  "short"),
    ("youtube_short_3",  "_upload_youtube_short_3",  "9x16.mp4",  "9:16",  "short"),
    ("facebook_reel",    "_upload_facebook_reel",    "9x16.mp4",  "9:16",  "reel"),
    ("instagram_reel",   "_upload_instagram_reel",   "9x16.mp4",  "9:16",  "reel"),
    ("linkedin_video",   "_upload_linkedin_video",   "9x16.mp4",  "9:16",  "video"),
    ("bluesky_post",     "_upload_bluesky_post",     "9x16.mp4",  "9:16",  "video"),
]

import sys as _sys


# ---------------------------------------------------------------------------
# Public orchestrator
# ---------------------------------------------------------------------------

def upload_all(
    output_dir: str,
    spec: Dict,
    config: Any,
) -> List[UploadResult]:
    """
    Upload to enabled platforms. Failures are isolated — one failure does not
    block the remaining uploads.
    """
    import src.stages.post as _self  # resolve current module so patches are visible

    enabled = set()
    platforms_str = getattr(config, "publish_platforms", "")
    if platforms_str:
        enabled = {p.strip() for p in platforms_str.split(",") if p.strip()}

    results: List[UploadResult] = []
    youtube_short_url = ""

    for platform_name, fn_name, file_name, aspect_ratio, content_type in _UPLOAD_FNS:
        if enabled and platform_name not in enabled:
            log.info("post.upload.skipped", platform=platform_name, reason="not in PUBLISH_PLATFORMS")
            results.append(UploadResult(
                platform=platform_name, status="skipped",
                file_name=file_name, aspect_ratio=aspect_ratio, content_type=content_type,
            ))
            continue
        log.info("post.upload.start", platform=platform_name)
        try:
            fn = getattr(_self, fn_name)
            if platform_name in ("linkedin_video", "facebook_reel", "bluesky_post"):
                data = fn(output_dir, spec, config, youtube_url=youtube_short_url)
            else:
                data = fn(output_dir, spec, config)
            if platform_name == "youtube_short" and data.get("platform_url"):
                youtube_short_url = data["platform_url"]
            result = UploadResult(
                platform=platform_name,
                status="completed",
                platform_id=data.get("platform_id", ""),
                platform_url=data.get("platform_url", ""),
                file_name=file_name,
                aspect_ratio=aspect_ratio,
                content_type=content_type,
            )
            log.info("post.upload.done", platform=platform_name, platform_id=result.platform_id)
        except Exception as exc:
            log.error("post.upload.failed", platform=platform_name, error=str(exc))
            result = UploadResult(
                platform=platform_name,
                status="failed",
                error_message=str(exc),
                file_name=file_name,
                aspect_ratio=aspect_ratio,
                content_type=content_type,
            )
        results.append(result)

    return results
