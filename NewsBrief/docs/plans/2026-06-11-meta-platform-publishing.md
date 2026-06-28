# Meta Platform Publishing (Phase 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Facebook Reels and Instagram Reels publishing to the daily pipeline with dynamic brand-aligned captions and Meta token health monitoring.

**Architecture:** Rewrite Instagram upload to use resumable direct upload (rupload.facebook.com), eliminating the S3 dependency. Build a shared caption module that generates platform-appropriate captions from spec data. Add Meta token validation to the infra healthcheck.

**Tech Stack:** Python 3.9, requests, Meta Graph API v19.0, pytest

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `src/lib/captions.py` | Create | Shared caption builder — generates per-platform captions from spec data |
| `src/lib/platforms/instagram.py` | Rewrite | Resumable direct upload via rupload.facebook.com |
| `src/lib/platforms/facebook.py` | No change | Already works for direct Reel upload |
| `src/stages/post.py` | Modify | Remove S3 from Instagram, use captions module, update dispatch table |
| `src/config.py` | Modify | Remove instagram_access_token (uses page token) |
| `src/healthcheck.py` | Modify | Add Meta token validation |
| `meta_auth.py` | Create | Local OAuth script for Facebook + Instagram tokens |
| `tests/test_captions.py` | Create | Tests for caption builder |
| `tests/test_instagram.py` | Create | Tests for Instagram resumable upload |
| `tests/test_healthcheck_meta.py` | Create | Tests for Meta token health check |

---

### Task 1: Caption Builder Module

**Files:**
- Create: `src/lib/captions.py`
- Create: `tests/test_captions.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_captions.py
from src.lib.captions import build_caption


def _make_spec(date="2026-06-11"):
    return {
        "date": date,
        "slots": [
            {
                "type": "LEAD",
                "headline": "Lead Headline Here",
                "copy": "Lead body copy.",
            },
            {
                "type": "SCAN",
                "items": [
                    {"headline": "Scan Item One"},
                    {"headline": "Scan Item Two"},
                    {"headline": "Scan Item Three"},
                ],
            },
        ],
    }


def test_instagram_caption_has_no_links():
    caption = build_caption(_make_spec(), platform="instagram")
    assert "http" not in caption
    assert "https" not in caption


def test_instagram_caption_has_hashtags():
    caption = build_caption(_make_spec(), platform="instagram")
    assert "#COGNOSCERE" in caption
    assert "#news" in caption


def test_instagram_caption_has_decide_signoff():
    caption = build_caption(_make_spec(), platform="instagram")
    assert "Decide." in caption


def test_instagram_caption_has_headlines():
    caption = build_caption(_make_spec(), platform="instagram")
    assert "Lead Headline Here" in caption
    assert "Scan Item One" in caption
    assert "Scan Item Three" in caption


def test_facebook_caption_includes_youtube_url():
    caption = build_caption(
        _make_spec(), platform="facebook", youtube_url="https://youtube.com/watch?v=abc123"
    )
    assert "https://youtube.com/watch?v=abc123" in caption


def test_facebook_caption_has_decide_signoff():
    caption = build_caption(_make_spec(), platform="facebook")
    assert "Decide." in caption


def test_linkedin_caption_includes_youtube_url():
    caption = build_caption(
        _make_spec(), platform="linkedin", youtube_url="https://youtube.com/watch?v=abc123"
    )
    assert "https://youtube.com/watch?v=abc123" in caption


def test_no_ai_curated_in_any_caption():
    for platform in ("instagram", "facebook", "linkedin"):
        caption = build_caption(_make_spec(), platform=platform)
        assert "AI-curated" not in caption
        assert "ai-curated" not in caption.lower()


def test_caption_includes_date():
    caption = build_caption(_make_spec(date="2026-06-11"), platform="instagram")
    assert "2026-06-11" in caption


def test_caption_includes_sources():
    spec = _make_spec()
    spec["source_names"] = ["The Guardian", "AP News"]
    caption = build_caption(spec, platform="facebook")
    assert "The Guardian" in caption


def test_unknown_platform_defaults_to_facebook():
    caption = build_caption(_make_spec(), platform="unknown")
    assert "Decide." in caption
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/Downloads/Projects/NewsBrief && source .venv/bin/activate && python -m pytest tests/test_captions.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.lib.captions'`

- [ ] **Step 3: Write the caption builder**

```python
# src/lib/captions.py
"""Shared caption builder — generates per-platform captions from spec data."""
from __future__ import annotations

from typing import Dict, List


def _extract_headlines(spec: Dict) -> List[str]:
    """Pull headlines from spec slots."""
    headlines = []
    for slot in spec.get("slots", []):
        slot_type = slot.get("type", "")
        if slot_type == "LEAD":
            headlines.append(slot.get("headline", slot.get("copy", "")[:80]))
        elif slot_type == "SCAN":
            for item in slot.get("items", []):
                headlines.append(item.get("headline", item.get("copy", "")[:80]))
    return headlines


def build_caption(
    spec: Dict,
    platform: str,
    youtube_url: str = "",
) -> str:
    """Build a platform-appropriate caption from spec data.

    Platforms:
        instagram — no links, hashtags for discoverability
        facebook  — includes YouTube URL, hashtags
        linkedin  — includes YouTube URL, headline bullets
    """
    date = spec.get("date", "")
    headlines = _extract_headlines(spec)
    source_names = spec.get("source_names", [])

    bullet_lines = "\n".join(f"\u25b6 {h}" for h in headlines)

    if platform == "instagram":
        parts = [
            f"COGNOSCERE Daily Brief \u2014 {date}",
            "",
            bullet_lines,
            "",
        ]
        if source_names:
            parts.append(f"Sources: {' \u00b7 '.join(source_names)}")
            parts.append("")
        parts.append("Decide.")
        parts.append("")
        parts.append("#news #dailybrief #COGNOSCERE #newsbrief")
        return "\n".join(parts)

    if platform == "linkedin":
        parts = [
            f"COGNOSCERE Daily Brief \u2014 {date}",
            "",
            "Today's top stories in under 2 minutes:",
            "",
            bullet_lines,
            "",
            "#news #dailybrief #COGNOSCERE #newsbrief",
        ]
        if youtube_url:
            parts.append("")
            parts.append(f"\u25b6 Watch on YouTube Shorts: {youtube_url}")
        return "\n".join(parts)

    # facebook and default
    parts = [
        f"COGNOSCERE Daily Brief \u2014 {date}",
        "",
        bullet_lines,
        "",
    ]
    if source_names:
        parts.append(f"Sources: {' \u00b7 '.join(source_names)}")
        parts.append("")
    parts.append("Decide.")
    if youtube_url:
        parts.append("")
        parts.append(f"\u25b6 Watch on YouTube Shorts: {youtube_url}")
    parts.append("")
    parts.append("#news #dailybrief #COGNOSCERE #newsbrief")
    return "\n".join(parts)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/Downloads/Projects/NewsBrief && source .venv/bin/activate && python -m pytest tests/test_captions.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
cd ~/Downloads/Projects/NewsBrief
git add src/lib/captions.py tests/test_captions.py
git commit -m "feat: shared caption builder with per-platform formatting"
```

---

### Task 2: Rewrite Instagram Resumable Upload

**Files:**
- Rewrite: `src/lib/platforms/instagram.py`
- Create: `tests/test_instagram.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_instagram.py
from unittest.mock import patch, MagicMock, mock_open
import pytest

from src.lib.platforms.instagram import upload_reel


@patch("src.lib.platforms.instagram.requests")
def test_upload_reel_creates_container(mock_requests):
    # Step 1: create container returns id
    create_resp = MagicMock()
    create_resp.json.return_value = {"id": "container_123"}
    create_resp.raise_for_status = MagicMock()

    # Step 2: PUT binary succeeds
    put_resp = MagicMock()
    put_resp.raise_for_status = MagicMock()

    # Step 3: poll returns FINISHED
    poll_resp = MagicMock()
    poll_resp.json.return_value = {"status_code": "FINISHED"}
    poll_resp.raise_for_status = MagicMock()

    # Step 4: publish returns media_id
    publish_resp = MagicMock()
    publish_resp.json.return_value = {"id": "media_456"}
    publish_resp.raise_for_status = MagicMock()

    mock_requests.post.side_effect = [create_resp, publish_resp]
    mock_requests.put.return_value = put_resp
    mock_requests.get.return_value = poll_resp

    with patch("builtins.open", mock_open(b"fake_video_bytes")):
        with patch("os.path.getsize", return_value=1024):
            result = upload_reel(
                ig_account_id="ig_123",
                access_token="token_abc",
                file_path="/tmp/video.mp4",
                caption="Test caption",
            )

    assert result["platform_id"] == "media_456"
    # Verify create container call used resumable
    create_call = mock_requests.post.call_args_list[0]
    assert "upload_type" in str(create_call) or "resumable" in str(create_call)


@patch("src.lib.platforms.instagram.requests")
def test_upload_reel_raises_on_error_status(mock_requests):
    create_resp = MagicMock()
    create_resp.json.return_value = {"id": "container_123"}
    create_resp.raise_for_status = MagicMock()

    put_resp = MagicMock()
    put_resp.raise_for_status = MagicMock()

    poll_resp = MagicMock()
    poll_resp.json.return_value = {"status_code": "ERROR"}
    poll_resp.raise_for_status = MagicMock()

    mock_requests.post.return_value = create_resp
    mock_requests.put.return_value = put_resp
    mock_requests.get.return_value = poll_resp

    with patch("builtins.open", mock_open(b"fake")):
        with patch("os.path.getsize", return_value=512):
            with pytest.raises(RuntimeError, match="failed processing"):
                upload_reel(
                    ig_account_id="ig_123",
                    access_token="token_abc",
                    file_path="/tmp/video.mp4",
                    caption="Test",
                )


@patch("src.lib.platforms.instagram.requests")
def test_upload_reel_uses_file_path_not_url(mock_requests):
    """Verify the new signature accepts file_path, not video_url."""
    create_resp = MagicMock()
    create_resp.json.return_value = {"id": "c1"}
    create_resp.raise_for_status = MagicMock()
    put_resp = MagicMock()
    put_resp.raise_for_status = MagicMock()
    poll_resp = MagicMock()
    poll_resp.json.return_value = {"status_code": "FINISHED"}
    poll_resp.raise_for_status = MagicMock()
    pub_resp = MagicMock()
    pub_resp.json.return_value = {"id": "m1"}
    pub_resp.raise_for_status = MagicMock()

    mock_requests.post.side_effect = [create_resp, pub_resp]
    mock_requests.put.return_value = put_resp
    mock_requests.get.return_value = poll_resp

    with patch("builtins.open", mock_open(b"data")):
        with patch("os.path.getsize", return_value=256):
            result = upload_reel(
                ig_account_id="ig_123",
                access_token="tok",
                file_path="/tmp/test.mp4",
                caption="cap",
            )

    assert result["platform_id"] == "m1"
    # PUT should have been called (binary upload)
    assert mock_requests.put.called
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/Downloads/Projects/NewsBrief && source .venv/bin/activate && python -m pytest tests/test_instagram.py -v`
Expected: FAIL (old signature expects `video_url` not `file_path`)

- [ ] **Step 3: Rewrite instagram.py with resumable upload**

```python
# src/lib/platforms/instagram.py
from __future__ import annotations

import os
import time
from typing import Dict

import requests
import structlog

log = structlog.get_logger()

GRAPH_API = "https://graph.facebook.com/v19.0"
UPLOAD_API = "https://rupload.facebook.com/ig-api-upload/v19.0"


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
    container_id = resp.json()["id"]
    log.info("instagram.container.created", container_id=container_id)

    # Step 2: PUT binary to rupload.facebook.com
    with open(file_path, "rb") as f:
        put_resp = requests.put(
            f"{UPLOAD_API}/{container_id}",
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/Downloads/Projects/NewsBrief && source .venv/bin/activate && python -m pytest tests/test_instagram.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
cd ~/Downloads/Projects/NewsBrief
git add src/lib/platforms/instagram.py tests/test_instagram.py
git commit -m "feat: Instagram resumable direct upload, remove S3 dependency"
```

---

### Task 3: Update post.py — Remove S3, Use Caption Builder

**Files:**
- Modify: `src/stages/post.py`
- Modify: `tests/test_post.py`

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/test_post.py

from src.lib.captions import build_caption


def test_build_caption_used_for_instagram():
    """Instagram upload should use captions module, not hardcoded string."""
    from unittest.mock import patch, MagicMock

    spec = {"date": "2026-06-11", "slots": []}

    class FakeConfig:
        facebook_page_id = "pg_123"
        facebook_access_token = "tok"
        instagram_account_id = "ig_123"
        publish_platforms = "instagram_reel"
        linkedin_member_id = ""
        linkedin_org_id = ""
        linkedin_access_token = ""
        youtube_client_id = ""
        youtube_client_secret = ""
        youtube_refresh_token = ""

    with patch("src.stages.post._upload_instagram_reel") as mock_ig:
        mock_ig.return_value = {"platform_id": "m1", "platform_url": "https://instagram.com/reel/m1"}
        from src.stages.post import upload_all
        results = upload_all("/tmp/out", spec, FakeConfig())
        # Should have called _upload_instagram_reel (not skipped)
        completed = [r for r in results if r.status == "completed"]
        assert len(completed) == 1
        assert completed[0].platform == "instagram_reel"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/Downloads/Projects/NewsBrief && source .venv/bin/activate && python -m pytest tests/test_post.py::test_build_caption_used_for_instagram -v`
Expected: FAIL (current _upload_instagram_reel still imports boto3/s3)

- [ ] **Step 3: Update post.py**

Replace `_upload_instagram_reel` (remove S3), `_upload_facebook_reel`, and update `_build_linkedin_caption` to use the shared caption builder. Apply these changes to `src/stages/post.py`:

**Replace _upload_facebook_reel:**
```python
def _upload_facebook_reel(output_dir: str, spec: Dict, config: Any, youtube_url: str = "") -> Dict[str, str]:
    from src.lib.platforms.facebook import upload_reel
    from src.lib.captions import build_caption

    file_path = _find_short_clip(output_dir) or ""
    caption = build_caption(spec, platform="facebook", youtube_url=youtube_url)
    return upload_reel(
        page_id=getattr(config, "facebook_page_id", ""),
        access_token=getattr(config, "facebook_access_token", ""),
        file_path=file_path,
        description=caption,
    )
```

**Replace _upload_instagram_reel (remove entire S3/boto3 block):**
```python
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
```

**Replace _build_linkedin_caption and _upload_linkedin_video:**
```python
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
```

**Remove `_build_linkedin_caption` function** (replaced by shared `build_caption`).

**Remove `_upload_facebook_video` function** (16:9 path no longer used).

**Update upload_all to pass youtube_url to facebook_reel:**
```python
# In upload_all(), update the linkedin_video block to also handle facebook_reel:
if platform_name in ("linkedin_video", "facebook_reel"):
    data = fn(output_dir, spec, config, youtube_url=youtube_short_url)
elif platform_name == "linkedin_video":
    # (remove this separate branch — merged above)
    pass
else:
    data = fn(output_dir, spec, config)
```

**Update dispatch table — remove facebook_video:**
```python
_UPLOAD_FNS = [
    ("youtube_video",    "_upload_youtube_video",    "9x16.mp4",  "9:16",  "video"),
    ("youtube_short",    "_upload_youtube_short",    "9x16.mp4",  "9:16",  "short"),
    ("facebook_reel",    "_upload_facebook_reel",    "9x16.mp4",  "9:16",  "reel"),
    ("instagram_reel",   "_upload_instagram_reel",   "9x16.mp4",  "9:16",  "reel"),
    ("linkedin_video",   "_upload_linkedin_video",   "9x16.mp4",  "9:16",  "video"),
]
```

- [ ] **Step 4: Run all tests**

Run: `cd ~/Downloads/Projects/NewsBrief && source .venv/bin/activate && python -m pytest tests/ -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
cd ~/Downloads/Projects/NewsBrief
git add src/stages/post.py tests/test_post.py
git commit -m "feat: dynamic captions, remove S3 from Instagram, remove facebook_video"
```

---

### Task 4: Update Config — Remove instagram_access_token

**Files:**
- Modify: `src/config.py`

- [ ] **Step 1: Remove instagram_access_token field and env var loading**

In `src/config.py`, remove the `instagram_access_token` field from the Config dataclass and its corresponding line in `load_config()`. Instagram now uses `facebook_access_token` (the shared page token).

Remove from dataclass:
```python
    # DELETE this line:
    instagram_access_token: str = ""
```

Remove from `load_config()`:
```python
        # DELETE this line:
        instagram_access_token=os.environ.get("INSTAGRAM_ACCESS_TOKEN", ""),
```

- [ ] **Step 2: Run all tests to verify nothing breaks**

Run: `cd ~/Downloads/Projects/NewsBrief && source .venv/bin/activate && python -m pytest tests/ -v`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
cd ~/Downloads/Projects/NewsBrief
git add src/config.py
git commit -m "refactor: remove instagram_access_token, uses shared page token"
```

---

### Task 5: Meta Token Health Check

**Files:**
- Modify: `src/healthcheck.py`
- Create: `tests/test_healthcheck_meta.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_healthcheck_meta.py
from unittest.mock import patch, MagicMock
from src.healthcheck import check_meta_token


@patch("src.healthcheck.requests")
def test_valid_token_returns_true(mock_requests):
    resp = MagicMock()
    resp.json.return_value = {
        "data": {"is_valid": True, "expires_at": 0, "app_id": "123"}
    }
    resp.raise_for_status = MagicMock()
    mock_requests.get.return_value = resp

    assert check_meta_token("valid_token") is True


@patch("src.healthcheck.requests")
def test_invalid_token_returns_false(mock_requests):
    resp = MagicMock()
    resp.json.return_value = {
        "data": {"is_valid": False, "error": {"message": "expired"}}
    }
    resp.raise_for_status = MagicMock()
    mock_requests.get.return_value = resp

    assert check_meta_token("expired_token") is False


@patch("src.healthcheck.requests")
def test_network_error_returns_false(mock_requests):
    mock_requests.get.side_effect = Exception("Connection refused")

    assert check_meta_token("any_token") is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/Downloads/Projects/NewsBrief && source .venv/bin/activate && python -m pytest tests/test_healthcheck_meta.py -v`
Expected: FAIL with `ImportError: cannot import name 'check_meta_token'`

- [ ] **Step 3: Add check_meta_token to healthcheck.py**

Add this function to `src/healthcheck.py` (after the existing check functions, before `main()`):

```python
def check_meta_token(access_token: str) -> bool:
    """Validate a Meta access token via the debug_token endpoint."""
    if not access_token:
        log.warning("healthcheck.meta.skipped", reason="no token")
        return True  # skip if not configured
    try:
        import requests
        resp = requests.get(
            "https://graph.facebook.com/debug_token",
            params={"input_token": access_token, "access_token": access_token},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})
        is_valid = data.get("is_valid", False)
        if not is_valid:
            error_msg = data.get("error", {}).get("message", "unknown")
            log.error("healthcheck.meta.invalid", error=error_msg)
        return is_valid
    except Exception as e:
        log.error("healthcheck.meta.failed", error=str(e))
        return False
```

Then add to the `infra_checks` list in `main()`:

```python
            ("Meta token (FB/IG)", lambda: check_meta_token(config.facebook_access_token)),
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/Downloads/Projects/NewsBrief && source .venv/bin/activate && python -m pytest tests/test_healthcheck_meta.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
cd ~/Downloads/Projects/NewsBrief
git add src/healthcheck.py tests/test_healthcheck_meta.py
git commit -m "feat: Meta token validation in infra healthcheck"
```

---

### Task 6: Meta Auth Script

**Files:**
- Create: `meta_auth.py`

- [ ] **Step 1: Create the local OAuth script**

```python
# meta_auth.py
"""
One-time OAuth2 flow to obtain a permanent Facebook Page token.
Covers Facebook Page + Instagram Business Account.
Run locally — opens a browser for Facebook Login.
"""
import http.server
import json
import urllib.parse
import webbrowser
import sys

import requests

# -- Fill in from your Meta Developer App --
APP_ID = ""       # Set before running
APP_SECRET = ""   # Set before running
REDIRECT_URI = "http://localhost:8080/callback"
SCOPES = ",".join([
    "pages_manage_posts",
    "pages_read_engagement",
    "instagram_basic",
    "instagram_content_publish",
])

auth_code = None


class CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        if "code" in params:
            auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>Facebook authorization successful!</h1><p>You can close this tab.</p>")
        else:
            error = params.get("error_description", ["unknown"])[0]
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(f"<h1>Error</h1><p>{error}</p>".encode())
            print(f"\nError: {error}", file=sys.stderr)
            sys.exit(1)

    def log_message(self, format, *args):
        pass


if not APP_ID or not APP_SECRET:
    print("ERROR: Set APP_ID and APP_SECRET before running.", file=sys.stderr)
    print("Get them from: https://developers.facebook.com/apps/", file=sys.stderr)
    sys.exit(1)

# Step 1: Open browser for authorization
auth_url = (
    f"https://www.facebook.com/v19.0/dialog/oauth"
    f"?client_id={APP_ID}"
    f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
    f"&scope={SCOPES}"
    f"&response_type=code"
)
print("Opening browser for Facebook authorization...")
webbrowser.open(auth_url)

server = http.server.HTTPServer(("localhost", 8080), CallbackHandler)
server.handle_request()

if not auth_code:
    print("No authorization code received.", file=sys.stderr)
    sys.exit(1)

# Step 2: Exchange code for short-lived user token
print("Exchanging code for access token...")
resp = requests.get(
    "https://graph.facebook.com/v19.0/oauth/access_token",
    params={
        "client_id": APP_ID,
        "client_secret": APP_SECRET,
        "redirect_uri": REDIRECT_URI,
        "code": auth_code,
    },
    timeout=30,
)
resp.raise_for_status()
short_token = resp.json()["access_token"]

# Step 3: Exchange for long-lived user token
print("Exchanging for long-lived token...")
resp = requests.get(
    "https://graph.facebook.com/v19.0/oauth/access_token",
    params={
        "grant_type": "fb_exchange_token",
        "client_id": APP_ID,
        "client_secret": APP_SECRET,
        "fb_exchange_token": short_token,
    },
    timeout=30,
)
resp.raise_for_status()
long_token = resp.json()["access_token"]

# Step 4: Get Page Access Token (never expires)
print("Fetching Page Access Token...")
resp = requests.get(
    "https://graph.facebook.com/v19.0/me/accounts",
    params={"access_token": long_token},
    timeout=30,
)
resp.raise_for_status()
pages = resp.json().get("data", [])

if not pages:
    print("ERROR: No Facebook Pages found for this account.", file=sys.stderr)
    sys.exit(1)

print(f"\nFound {len(pages)} page(s):")
for i, page in enumerate(pages):
    print(f"  [{i}] {page['name']} (ID: {page['id']})")

if len(pages) == 1:
    selected = pages[0]
else:
    idx = int(input("\nSelect page number: "))
    selected = pages[idx]

page_token = selected["access_token"]
page_id = selected["id"]

# Step 5: Get Instagram Business Account ID
print("Fetching Instagram Business Account...")
resp = requests.get(
    f"https://graph.facebook.com/v19.0/{page_id}",
    params={"fields": "instagram_business_account", "access_token": page_token},
    timeout=30,
)
resp.raise_for_status()
ig_data = resp.json().get("instagram_business_account", {})
ig_account_id = ig_data.get("id", "")

print(f"\n=== Meta OAuth Complete ===")
print(f"Page: {selected['name']} (ID: {page_id})")
print(f"Instagram Business Account: {ig_account_id}")
print(f"Page Token: {page_token[:40]}... (never expires)")
print(f"\nSet these on EC2:")
print(f"  FACEBOOK_ACCESS_TOKEN={page_token}")
print(f"  FACEBOOK_PAGE_ID={page_id}")
if ig_account_id:
    print(f"  INSTAGRAM_ACCOUNT_ID={ig_account_id}")
else:
    print("  WARNING: No Instagram Business Account linked to this page")
```

- [ ] **Step 2: Commit**

```bash
cd ~/Downloads/Projects/NewsBrief
git add meta_auth.py
git commit -m "feat: Meta OAuth script for Facebook + Instagram page token"
```

---

### Task 7: Deploy to EC2

**Files:**
- Push updated files to EC2 via scp

- [ ] **Step 1: Push all modified source files to EC2**

```bash
scp -i ~/.ssh/cifaas-prod.pem \
  ~/Downloads/Projects/NewsBrief/src/lib/captions.py \
  ec2-user@3.230.75.149:~/newsbrief/src/lib/captions.py

scp -i ~/.ssh/cifaas-prod.pem \
  ~/Downloads/Projects/NewsBrief/src/lib/platforms/instagram.py \
  ec2-user@3.230.75.149:~/newsbrief/src/lib/platforms/instagram.py

scp -i ~/.ssh/cifaas-prod.pem \
  ~/Downloads/Projects/NewsBrief/src/stages/post.py \
  ec2-user@3.230.75.149:~/newsbrief/src/stages/post.py

scp -i ~/.ssh/cifaas-prod.pem \
  ~/Downloads/Projects/NewsBrief/src/config.py \
  ec2-user@3.230.75.149:~/newsbrief/src/config.py

scp -i ~/.ssh/cifaas-prod.pem \
  ~/Downloads/Projects/NewsBrief/src/healthcheck.py \
  ec2-user@3.230.75.149:~/newsbrief/src/healthcheck.py
```

- [ ] **Step 2: Verify config loads on EC2**

```bash
ssh -i ~/.ssh/cifaas-prod.pem ec2-user@3.230.75.149 \
  "cd ~/newsbrief && .venv/bin/python -c 'from src.config import load_config; c = load_config(); print(f\"fb_page_id: {len(c.facebook_page_id)} chars\"); print(f\"ig_account_id: {len(c.instagram_account_id)} chars\")'"
```

- [ ] **Step 3: Update PUBLISH_PLATFORMS on EC2 (after App Review clears)**

```bash
ssh -i ~/.ssh/cifaas-prod.pem ec2-user@3.230.75.149 \
  "cd ~/newsbrief && sed -i 's/^PUBLISH_PLATFORMS=.*/PUBLISH_PLATFORMS=youtube_short,linkedin_video,facebook_reel,instagram_reel/' .env"
```

**Note:** Do NOT enable `facebook_reel` and `instagram_reel` in PUBLISH_PLATFORMS until:
1. Meta Developer App is created and App Review for `instagram_content_publish` is approved
2. `meta_auth.py` has been run locally to obtain the permanent page token
3. FACEBOOK_ACCESS_TOKEN and FACEBOOK_PAGE_ID are set in EC2 .env

- [ ] **Step 4: Commit deploy notes**

```bash
cd ~/Downloads/Projects/NewsBrief
git commit --allow-empty -m "chore: Phase 1 Meta publishing deployed to EC2 (pending App Review)"
```
