# NewsBrief Plan D: Distribution + Operations Implementation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the publish gate, platform upload clients (YouTube, Facebook, Instagram, LinkedIn), S3 presigned URL support, Google Drive archiving, run logging, health checks, alerting, and the complete CLI — making the pipeline fully operational end-to-end.

**Architecture:** Stage modules for GATE, POST, ARCHIVE, and LOG. Platform-specific upload clients isolated in `src/lib/platforms/`. Health check and status CLI tools. Jinja2 templates for captions and alert emails. Each platform upload is independent — one failure does not block others.

**Tech Stack:** Python 3.11+, google-api-python-client, google-auth, boto3, requests, Jinja2, structlog, pytest

**Depends on:** Plans A, B, C (full pipeline stages 1-5)

---

## File Structure

```
src/
  stages/
    gate.py                       # Stage 5b: Publish gate logic
    post.py                       # Stage 6: Platform uploads orchestration
    archive.py                    # Stage 7: Google Drive archiving
    log.py                        # Stage 8: Write video_runs / video_uploads records
  lib/
    platforms/
      __init__.py
      youtube.py                  # YouTube Data API v3 upload
      facebook.py                 # Facebook Graph API upload (video + Reel)
      instagram.py                # Instagram Graph API upload (via presigned URL)
      linkedin.py                 # LinkedIn Marketing API upload
      s3.py                       # S3/R2 presigned URL generation
      drive.py                    # Google Drive archive upload
    alert.py                      # Email alerting (success/failure)
  templates/
    youtube_description.j2
    linkedin_caption.j2
    alert_success.j2
    alert_failure.j2
    gate_review.j2
  healthcheck.py                  # Pre-flight health check CLI
  status.py                       # Status/history CLI
  cleanup.py                      # Monthly spec/log cleanup
tests/
  test_gate.py
  test_post.py
  test_s3.py
  test_archive.py
  test_log_stage.py
  test_alert.py
  test_healthcheck.py
```

---

### Task 1: Jinja2 Caption Templates

**Files:**
- Create: `src/templates/youtube_description.j2`
- Create: `src/templates/linkedin_caption.j2`
- Create: `src/templates/alert_success.j2`
- Create: `src/templates/alert_failure.j2`
- Create: `src/templates/gate_review.j2`

- [ ] **Step 1: Create youtube_description.j2**

```jinja2
COGNOSCERE Daily Brief -- {{ date }} | Issue #{{ issue_number }}

{{ today_in_one_breath }}

STORIES COVERED:
{% for story in stories %}
{{ story.headline }} [{{ story.cif_tag }}]
{% endfor %}

---
Every source cited. Every claim tagged. Read the full record:
{{ base_url }}/news/{{ date_slug }}/?utm_source=youtube&utm_medium=video&utm_campaign=cdb-{{ date_slug }}&utm_content={{ content_id }}

Subscribe to the daily email: https://cognoscerellc.substack.com/?utm_source=youtube&utm_medium=video&utm_campaign=cdb-{{ date_slug }}&utm_content={{ content_id }}
CIFaaS intelligence platform: https://cifaas.cognoscerellc.com/?utm_source=youtube&utm_medium=video&utm_campaign=cdb-{{ date_slug }}&utm_content={{ content_id }}

COGNOSCERE LLC | A Service-Disabled Veteran-Owned Small Business
Green Cove Springs, Florida

#DailyBrief #Intelligence #News #COGNOSCERE
```

- [ ] **Step 2: Create linkedin_caption.j2**

```jinja2
{{ why_it_matters }}

Stories covered: {{ story_list }}

Full analysis and sourcing: {{ base_url }}/news/{{ date_slug }}/?utm_source=linkedin&utm_medium=video&utm_campaign=cdb-{{ date_slug }}&utm_content=anchor

#COGNOSCERE #Intelligence #DailyBrief
```

- [ ] **Step 3: Create alert_success.j2**

```jinja2
[NewsBrief] {{ date }} - {{ upload_count }}/{{ total_platforms }} platforms posted

Issue #{{ issue_number }} | Duration: {{ duration }}

UPLOADS:
{% for upload in uploads %}
  {{ upload.platform | ljust(22) }} {{ upload.status | upper }}  {{ upload.url or '' }}
{% endfor %}

COSTS:
  ElevenLabs: {{ elevenlabs_chars }} chars (~${{ elevenlabs_cost }})
  Claude API: {{ llm_input_tokens }} in / {{ llm_output_tokens }} out (~${{ llm_cost }})

ARCHIVE: {{ drive_url or 'N/A' }}
{% if pronunciation_new > 0 %}
PRONUNCIATION: {{ pronunciation_new }} new words flagged for review
{% endif %}
```

- [ ] **Step 4: Create alert_failure.j2**

```jinja2
[NewsBrief] FAILED - {{ date }} - Stage: {{ failed_stage }}

Issue #{{ issue_number }} | Failed at: {{ failed_stage }} after {{ duration }}

ERROR: {{ error_message }}

ACTION REQUIRED:
  - Manual re-run: python src/run.py --date {{ date }}
  - Check logs: logs/newsbrief-{{ date }}.log
```

- [ ] **Step 5: Create gate_review.j2**

```jinja2
[NewsBrief] Review Required - {{ date }} | Issue #{{ issue_number }}

PUBLISH MODE: {{ publish_mode }}
{% if requires_review %}
REASON: Unknown proper nouns in HOOK/LEAD: {{ unknown_words | join(', ') }}
{% endif %}

--- SCRIPT ---

[HOOK]
{{ hook }}

[LEAD]
{{ lead }}

[SCAN]
{{ scan }}

[WHY IT MATTERS]
{{ why }}

[CLOSE]
{{ close }}

---

Word count: {{ word_count }}

To approve: python src/run.py --date {{ date }} --approve
To kill: python src/run.py --date {{ date }} --kill
```

- [ ] **Step 6: Commit**

```bash
git add src/templates/
git commit -m "feat: Jinja2 templates for captions, alerts, and gate review"
```

---

### Task 2: S3 Presigned URL Client

**Files:**
- Create: `src/lib/platforms/s3.py`
- Create: `src/lib/platforms/__init__.py`
- Create: `tests/test_s3.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_s3.py
from unittest.mock import MagicMock, patch
import pytest


def test_upload_and_get_presigned_url():
    from src.lib.platforms.s3 import upload_for_presigned_url

    mock_s3 = MagicMock()
    mock_s3.generate_presigned_url.return_value = "https://bucket.s3.amazonaws.com/clip.mp4?sig=abc"

    result = upload_for_presigned_url(
        s3_client=mock_s3,
        bucket="newsbrief-temp",
        file_path="/tmp/clip.mp4",
        object_key="2026-06-10/clip-C3.mp4",
        expires_in=900,
    )

    assert "s3.amazonaws.com" in result
    mock_s3.upload_file.assert_called_once_with(
        "/tmp/clip.mp4", "newsbrief-temp", "2026-06-10/clip-C3.mp4"
    )
    mock_s3.generate_presigned_url.assert_called_once()


def test_presigned_url_uses_correct_expiry():
    from src.lib.platforms.s3 import upload_for_presigned_url

    mock_s3 = MagicMock()
    mock_s3.generate_presigned_url.return_value = "https://example.com/signed"

    upload_for_presigned_url(
        s3_client=mock_s3,
        bucket="b",
        file_path="/tmp/f.mp4",
        object_key="k",
        expires_in=600,
    )

    call_kwargs = mock_s3.generate_presigned_url.call_args.kwargs
    assert call_kwargs["ExpiresIn"] == 600
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_s3.py -v`
Expected: FAIL (ImportError)

- [ ] **Step 3: Write minimal implementation**

```python
# src/lib/platforms/__init__.py
# Platform upload clients

# src/lib/platforms/s3.py
from __future__ import annotations

import structlog

log = structlog.get_logger()


def upload_for_presigned_url(
    s3_client,
    bucket: str,
    file_path: str,
    object_key: str,
    expires_in: int = 900,
) -> str:
    log.info("s3.upload", bucket=bucket, key=object_key)

    s3_client.upload_file(file_path, bucket, object_key)

    url = s3_client.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": bucket, "Key": object_key},
        ExpiresIn=expires_in,
    )

    log.info("s3.presigned_url_generated", expires_in=expires_in)
    return url
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_s3.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/lib/platforms/ tests/test_s3.py
git commit -m "feat: S3/R2 presigned URL client for Instagram uploads"
```

---

### Task 3: Platform Upload Clients (YouTube, Facebook, Instagram, LinkedIn)

**Files:**
- Create: `src/lib/platforms/youtube.py`
- Create: `src/lib/platforms/facebook.py`
- Create: `src/lib/platforms/instagram.py`
- Create: `src/lib/platforms/linkedin.py`

These are API integration modules. Tests use mocks for all HTTP calls.

- [ ] **Step 1: Create youtube.py**

```python
# src/lib/platforms/youtube.py
from __future__ import annotations

from typing import Any, Dict, Optional

import structlog
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

log = structlog.get_logger()


def get_youtube_client(
    client_id: str, client_secret: str, refresh_token: str
) -> Any:
    credentials = Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri="https://oauth2.googleapis.com/token",
    )
    return build("youtube", "v3", credentials=credentials)


def upload_video(
    youtube_client: Any,
    file_path: str,
    title: str,
    description: str,
    tags: list[str],
    category_id: str = "25",
    thumbnail_path: Optional[str] = None,
) -> Dict[str, str]:
    log.info("youtube.upload.start", title=title)

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category_id,
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(file_path, mimetype="video/mp4", resumable=True)
    request = youtube_client.videos().insert(
        part="snippet,status", body=body, media_body=media
    )
    response = request.execute()

    video_id = response["id"]
    video_url = f"https://youtube.com/watch?v={video_id}"

    if thumbnail_path:
        youtube_client.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(thumbnail_path, mimetype="image/png"),
        ).execute()
        log.info("youtube.thumbnail.uploaded", video_id=video_id)

    log.info("youtube.upload.done", video_id=video_id, url=video_url)
    return {"platform_id": video_id, "platform_url": video_url}
```

- [ ] **Step 2: Create facebook.py**

```python
# src/lib/platforms/facebook.py
from __future__ import annotations

from typing import Dict

import requests
import structlog

log = structlog.get_logger()

GRAPH_API = "https://graph.facebook.com/v19.0"


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
    log.info("facebook.reel.upload.start")

    with open(file_path, "rb") as f:
        resp = requests.post(
            f"{GRAPH_API}/{page_id}/video_reels",
            files={"source": f},
            data={"description": description, "access_token": access_token},
            timeout=300,
        )

    resp.raise_for_status()
    data = resp.json()
    post_id = data.get("id", "")

    log.info("facebook.reel.upload.done", post_id=post_id)
    return {"platform_id": post_id, "platform_url": f"https://facebook.com/reel/{post_id}"}
```

- [ ] **Step 3: Create instagram.py**

```python
# src/lib/platforms/instagram.py
from __future__ import annotations

import time
from typing import Dict

import requests
import structlog

log = structlog.get_logger()

GRAPH_API = "https://graph.facebook.com/v19.0"


def upload_reel(
    ig_account_id: str,
    access_token: str,
    video_url: str,
    caption: str,
    max_poll_seconds: int = 300,
) -> Dict[str, str]:
    log.info("instagram.reel.upload.start")

    # Step 1: Create container
    resp = requests.post(
        f"{GRAPH_API}/{ig_account_id}/media",
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
        raise TimeoutError(f"Instagram container {container_id} stuck in PROCESSING after {max_poll_seconds}s")

    # Step 3: Publish
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

- [ ] **Step 4: Create linkedin.py**

```python
# src/lib/platforms/linkedin.py
from __future__ import annotations

from typing import Dict

import requests
import structlog

log = structlog.get_logger()

API_BASE = "https://api.linkedin.com/v2"


def upload_video(
    org_id: str,
    access_token: str,
    file_path: str,
    caption: str,
    title: str,
) -> Dict[str, str]:
    headers = {"Authorization": f"Bearer {access_token}"}
    log.info("linkedin.upload.start")

    # Step 1: Register upload
    register_resp = requests.post(
        f"{API_BASE}/assets?action=registerUpload",
        headers=headers,
        json={
            "registerUploadRequest": {
                "owner": f"urn:li:organization:{org_id}",
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
            "author": f"urn:li:organization:{org_id}",
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
    post_urn = post_resp.headers.get("X-RestLi-Id", "")

    log.info("linkedin.upload.done", post_urn=post_urn)
    return {"platform_id": post_urn, "platform_url": f"https://linkedin.com/feed/update/{post_urn}"}
```

- [ ] **Step 5: Commit**

```bash
git add src/lib/platforms/
git commit -m "feat: platform upload clients — YouTube, Facebook, Instagram, LinkedIn"
```

---

### Task 4: Google Drive Archive Client

**Files:**
- Create: `src/lib/platforms/drive.py`
- Create: `tests/test_archive.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_archive.py
from unittest.mock import MagicMock, patch
import pytest


def test_archive_creates_date_folder():
    from src.stages.archive import archive_to_drive

    mock_drive = MagicMock()
    # Mock folder creation
    mock_drive.files.return_value.create.return_value.execute.return_value = {"id": "folder123"}
    # Mock file list (empty — folder doesn't exist yet)
    mock_drive.files.return_value.list.return_value.execute.return_value = {"files": []}

    with patch("src.stages.archive.get_drive_service", return_value=mock_drive):
        with patch("src.stages.archive.upload_file_to_drive"):
            archive_to_drive(
                artifacts_dir="/tmp/2026-06-10",
                parent_folder_id="root123",
                sa_key_path="/fake/key.json",
                date_str="2026-06-10",
            )

    # Verify folder creation was called
    mock_drive.files.return_value.create.assert_called()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_archive.py -v`
Expected: FAIL (ImportError)

- [ ] **Step 3: Create drive.py**

```python
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
```

- [ ] **Step 4: Create archive.py stage**

```python
# src/stages/archive.py
from __future__ import annotations

import os
from typing import Optional

import structlog

from src.lib.platforms.drive import create_folder, get_drive_service, upload_file_to_drive

log = structlog.get_logger()


def archive_to_drive(
    artifacts_dir: str,
    parent_folder_id: str,
    sa_key_path: str,
    date_str: str,
) -> Optional[str]:
    log.info("archive.start", dir=artifacts_dir, date=date_str)

    service = get_drive_service(sa_key_path)

    # Create date-stamped folder
    folder_id = create_folder(service, date_str, parent_folder_id)
    log.info("archive.folder.created", folder_id=folder_id)

    # Upload all files in artifacts dir
    uploaded = 0
    for filename in os.listdir(artifacts_dir):
        filepath = os.path.join(artifacts_dir, filename)
        if os.path.isfile(filepath):
            upload_file_to_drive(service, filepath, folder_id, filename)
            uploaded += 1

    # Also upload from audio subdirectory if it exists
    audio_dir = os.path.join(artifacts_dir, "audio")
    if os.path.isdir(audio_dir):
        for filename in os.listdir(audio_dir):
            filepath = os.path.join(audio_dir, filename)
            if os.path.isfile(filepath):
                upload_file_to_drive(service, filepath, folder_id, f"audio/{filename}")
                uploaded += 1

    drive_url = f"https://drive.google.com/drive/folders/{folder_id}"
    log.info("archive.done", files_uploaded=uploaded, url=drive_url)
    return drive_url
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_archive.py -v`
Expected: 1 passed

- [ ] **Step 6: Commit**

```bash
git add src/lib/platforms/drive.py src/stages/archive.py tests/test_archive.py
git commit -m "feat: Google Drive archive client and Stage 7 ARCHIVE"
```

---

### Task 5: Stage 5b — GATE (Publish Gate)

**Files:**
- Create: `src/stages/gate.py`
- Create: `tests/test_gate.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_gate.py
import pytest


def test_gate_preview_mode_blocks():
    from src.stages.gate import check_gate, GateDecision

    decision = check_gate(
        publish_mode="preview",
        requires_review=False,
        approved=False,
    )
    assert decision == GateDecision.BLOCKED
    assert not decision.should_publish


def test_gate_preview_mode_with_approve_passes():
    from src.stages.gate import check_gate, GateDecision

    decision = check_gate(
        publish_mode="preview",
        requires_review=False,
        approved=True,
    )
    assert decision == GateDecision.APPROVED


def test_gate_auto_mode_passes():
    from src.stages.gate import check_gate, GateDecision

    decision = check_gate(
        publish_mode="auto",
        requires_review=False,
        approved=False,
    )
    assert decision == GateDecision.AUTO


def test_gate_auto_mode_blocked_by_review_flag():
    from src.stages.gate import check_gate, GateDecision

    decision = check_gate(
        publish_mode="auto",
        requires_review=True,
        approved=False,
    )
    assert decision == GateDecision.BLOCKED


def test_gate_mode_passes_without_kill():
    from src.stages.gate import check_gate, GateDecision

    decision = check_gate(
        publish_mode="gate",
        requires_review=False,
        approved=False,
        killed=False,
    )
    assert decision == GateDecision.AUTO


def test_gate_mode_blocked_by_kill():
    from src.stages.gate import check_gate, GateDecision

    decision = check_gate(
        publish_mode="gate",
        requires_review=False,
        approved=False,
        killed=True,
    )
    assert decision == GateDecision.KILLED
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_gate.py -v`
Expected: FAIL (ImportError)

- [ ] **Step 3: Write minimal implementation**

```python
# src/stages/gate.py
from __future__ import annotations

from enum import Enum

import structlog

log = structlog.get_logger()


class GateDecision(Enum):
    AUTO = "auto"
    APPROVED = "approved"
    BLOCKED = "blocked"
    KILLED = "killed"

    @property
    def should_publish(self) -> bool:
        return self in (GateDecision.AUTO, GateDecision.APPROVED)


def check_gate(
    publish_mode: str,
    requires_review: bool,
    approved: bool = False,
    killed: bool = False,
) -> GateDecision:
    log.info("gate.check", mode=publish_mode, requires_review=requires_review, approved=approved, killed=killed)

    # requires_review overrides auto mode (R8 proper-noun gate)
    if requires_review and not approved:
        log.warning("gate.blocked.review_required")
        return GateDecision.BLOCKED

    if publish_mode == "preview":
        if approved:
            return GateDecision.APPROVED
        log.info("gate.blocked.preview_mode")
        return GateDecision.BLOCKED

    if publish_mode == "gate":
        if killed:
            return GateDecision.KILLED
        return GateDecision.AUTO

    if publish_mode == "auto":
        return GateDecision.AUTO

    log.warning("gate.unknown_mode", mode=publish_mode)
    return GateDecision.BLOCKED
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_gate.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add src/stages/gate.py tests/test_gate.py
git commit -m "feat: Stage 5b GATE — publish gate with preview/gate/auto modes"
```

---

### Task 6: Stage 6 — POST (Upload Orchestration)

**Files:**
- Create: `src/stages/post.py`
- Create: `tests/test_post.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_post.py
from unittest.mock import MagicMock, patch
import pytest


def test_post_uploads_to_all_platforms():
    from src.stages.post import upload_all, UploadResult

    with patch("src.stages.post._upload_youtube_video", return_value={"platform_id": "yt1", "platform_url": "https://yt/1"}), \
         patch("src.stages.post._upload_youtube_short", return_value={"platform_id": "yt2", "platform_url": "https://yt/2"}), \
         patch("src.stages.post._upload_facebook_video", return_value={"platform_id": "fb1", "platform_url": "https://fb/1"}), \
         patch("src.stages.post._upload_facebook_reel", return_value={"platform_id": "fb2", "platform_url": "https://fb/2"}), \
         patch("src.stages.post._upload_instagram_reel", return_value={"platform_id": "ig1", "platform_url": "https://ig/1"}), \
         patch("src.stages.post._upload_linkedin_video", return_value={"platform_id": "li1", "platform_url": "https://li/1"}):

        results = upload_all(
            output_dir="/tmp/output",
            spec={"date": "2026-06-10", "clips": [], "slots": []},
            config=MagicMock(),
        )

    assert len(results) == 6
    succeeded = [r for r in results if r.status == "completed"]
    assert len(succeeded) == 6


def test_post_isolates_platform_failures():
    from src.stages.post import upload_all

    with patch("src.stages.post._upload_youtube_video", return_value={"platform_id": "yt1", "platform_url": ""}), \
         patch("src.stages.post._upload_youtube_short", side_effect=Exception("YT Short failed")), \
         patch("src.stages.post._upload_facebook_video", return_value={"platform_id": "fb1", "platform_url": ""}), \
         patch("src.stages.post._upload_facebook_reel", return_value={"platform_id": "fb2", "platform_url": ""}), \
         patch("src.stages.post._upload_instagram_reel", return_value={"platform_id": "ig1", "platform_url": ""}), \
         patch("src.stages.post._upload_linkedin_video", return_value={"platform_id": "li1", "platform_url": ""}):

        results = upload_all(
            output_dir="/tmp/output",
            spec={"date": "2026-06-10", "clips": [], "slots": []},
            config=MagicMock(),
        )

    failed = [r for r in results if r.status == "failed"]
    succeeded = [r for r in results if r.status == "completed"]
    assert len(failed) == 1
    assert len(succeeded) == 5
    assert failed[0].platform == "youtube_short"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_post.py -v`
Expected: FAIL (ImportError)

- [ ] **Step 3: Write minimal implementation**

```python
# src/stages/post.py
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import structlog

log = structlog.get_logger()


@dataclass
class UploadResult:
    platform: str
    status: str  # completed | failed | skipped
    platform_id: str = ""
    platform_url: str = ""
    error_message: str = ""
    file_name: str = ""
    aspect_ratio: str = ""
    content_type: str = ""
    clip_id: str = ""


def _upload_youtube_video(output_dir: str, spec: dict, config: Any) -> Dict[str, str]:
    from src.lib.platforms.youtube import get_youtube_client, upload_video
    client = get_youtube_client(config.youtube_client_id, config.youtube_client_secret, config.youtube_refresh_token)
    return upload_video(
        client,
        file_path=os.path.join(output_dir, "anchor-16x9.mp4"),
        title=spec.get("platform_meta", {}).get("youtube_title", f"COGNOSCERE Daily Brief - {spec['date']}"),
        description=spec.get("platform_meta", {}).get("youtube_description", ""),
        tags=spec.get("platform_meta", {}).get("youtube_tags", ["news", "COGNOSCERE"]),
        thumbnail_path=os.path.join(output_dir, "thumbnail.png"),
    )


def _upload_youtube_short(output_dir: str, spec: dict, config: Any) -> Dict[str, str]:
    from src.lib.platforms.youtube import get_youtube_client, upload_video
    client = get_youtube_client(config.youtube_client_id, config.youtube_client_secret, config.youtube_refresh_token)
    clip_file = _find_clip_file(output_dir, "C1")
    return upload_video(
        client,
        file_path=clip_file,
        title=spec.get("platform_meta", {}).get("youtube_short_title", "#shorts"),
        description="Full brief on our channel.",
        tags=["shorts", "news", "COGNOSCERE"],
    )


def _upload_facebook_video(output_dir: str, spec: dict, config: Any) -> Dict[str, str]:
    from src.lib.platforms.facebook import upload_video
    return upload_video(
        page_id=config.fb_page_id,
        access_token=config.fb_page_access_token,
        file_path=os.path.join(output_dir, "anchor-16x9.mp4"),
        description=spec.get("platform_meta", {}).get("facebook_caption", ""),
    )


def _upload_facebook_reel(output_dir: str, spec: dict, config: Any) -> Dict[str, str]:
    from src.lib.platforms.facebook import upload_reel
    clip_file = _find_best_clip(output_dir)
    return upload_reel(
        page_id=config.fb_page_id,
        access_token=config.fb_page_access_token,
        file_path=clip_file,
        description=spec.get("platform_meta", {}).get("facebook_reel_caption", ""),
    )


def _upload_instagram_reel(output_dir: str, spec: dict, config: Any) -> Dict[str, str]:
    import boto3
    from src.lib.platforms.s3 import upload_for_presigned_url
    from src.lib.platforms.instagram import upload_reel

    clip_file = _find_best_clip(output_dir)
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=config.s3_access_key,
        aws_secret_access_key=config.s3_secret_key,
    )
    presigned_url = upload_for_presigned_url(
        s3_client=s3_client,
        bucket=config.s3_bucket,
        file_path=clip_file,
        object_key=f"{spec['date']}/{os.path.basename(clip_file)}",
        expires_in=900,
    )
    return upload_reel(
        ig_account_id=config.ig_business_account_id,
        access_token=config.fb_page_access_token,
        video_url=presigned_url,
        caption=spec.get("platform_meta", {}).get("instagram_caption", ""),
    )


def _upload_linkedin_video(output_dir: str, spec: dict, config: Any) -> Dict[str, str]:
    from src.lib.platforms.linkedin import upload_video
    return upload_video(
        org_id=config.linkedin_org_id,
        access_token=config.linkedin_access_token,
        file_path=os.path.join(output_dir, "anchor-16x9.mp4"),
        caption=spec.get("platform_meta", {}).get("linkedin_caption", ""),
        title=f"COGNOSCERE Daily Brief - {spec['date']}",
    )


def _find_clip_file(output_dir: str, clip_id: str) -> str:
    for f in os.listdir(output_dir):
        if f.startswith(f"clip-{clip_id}") and f.endswith(".mp4"):
            return os.path.join(output_dir, f)
    return os.path.join(output_dir, "anchor-9x16.mp4")


def _find_best_clip(output_dir: str) -> str:
    # Default: C1 (lead story). Fallback to anchor 9:16.
    return _find_clip_file(output_dir, "C1")


_UPLOAD_FNS = [
    ("youtube_video", _upload_youtube_video, "anchor-16x9.mp4", "16x9", "anchor"),
    ("youtube_short", _upload_youtube_short, "clip-C1-9x16.mp4", "9x16", "micro_clip"),
    ("facebook_video", _upload_facebook_video, "anchor-16x9.mp4", "16x9", "anchor"),
    ("facebook_reel", _upload_facebook_reel, "clip-9x16.mp4", "9x16", "micro_clip"),
    ("instagram_reel", _upload_instagram_reel, "clip-9x16.mp4", "9x16", "micro_clip"),
    ("linkedin_video", _upload_linkedin_video, "anchor-16x9.mp4", "16x9", "anchor"),
]


def upload_all(
    output_dir: str,
    spec: dict,
    config: Any,
) -> List[UploadResult]:
    results: List[UploadResult] = []

    for platform, fn, file_name, aspect, content_type in _UPLOAD_FNS:
        try:
            log.info("post.upload.start", platform=platform)
            result_data = fn(output_dir, spec, config)
            results.append(UploadResult(
                platform=platform,
                status="completed",
                platform_id=result_data.get("platform_id", ""),
                platform_url=result_data.get("platform_url", ""),
                file_name=file_name,
                aspect_ratio=aspect,
                content_type=content_type,
            ))
            log.info("post.upload.done", platform=platform)
        except Exception as e:
            log.error("post.upload.failed", platform=platform, error=str(e))
            results.append(UploadResult(
                platform=platform,
                status="failed",
                error_message=str(e),
                file_name=file_name,
                aspect_ratio=aspect,
                content_type=content_type,
            ))

    return results
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_post.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/stages/post.py tests/test_post.py
git commit -m "feat: Stage 6 POST — platform upload orchestration with failure isolation"
```

---

### Task 7: Stage 8 — LOG + Alert

**Files:**
- Create: `src/stages/log.py`
- Create: `src/lib/alert.py`

- [ ] **Step 1: Create log.py**

```python
# src/stages/log.py
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List

import structlog
from sqlalchemy.orm import Session

from src.models import VideoRun, VideoUpload, VideoScript
from src.stages.post import UploadResult

log = structlog.get_logger()


def save_run(session: Session, run: VideoRun) -> None:
    log.info("log.save_run", run_id=run.id, status=run.status)
    session.merge(run)
    session.commit()


def save_uploads(
    session: Session,
    run_id: str,
    upload_results: List[UploadResult],
) -> None:
    for r in upload_results:
        upload = VideoUpload(
            run_id=run_id,
            platform=r.platform,
            status=r.status,
            platform_id=r.platform_id or None,
            platform_url=r.platform_url or None,
            file_name=r.file_name,
            aspect_ratio=r.aspect_ratio,
            content_type=r.content_type,
            clip_id=r.clip_id or None,
            error_message=r.error_message or None,
        )
        session.add(upload)

    session.commit()
    log.info("log.uploads.saved", count=len(upload_results))


def save_script(
    session: Session,
    run_id: str,
    brief_id: int,
    script_result,
    spec: dict | None = None,
) -> None:
    vs = VideoScript(
        run_id=run_id,
        brief_id=brief_id,
        hook_copy=script_result.hook,
        lead_copy=script_result.lead,
        scan_copy=script_result.full_scan,
        why_copy=script_result.why,
        close_copy=script_result.close,
        lead_cluster_id=script_result.lead_cluster_id,
        scan_cluster_ids=script_result.scan_cluster_ids,
        selection_rationale=script_result.selection_rationale,
        platform_meta=script_result.platform_meta,
        remotion_spec=spec,
    )
    session.add(vs)
    session.commit()
    log.info("log.script.saved", run_id=run_id)
```

- [ ] **Step 2: Create alert.py**

```python
# src/lib/alert.py
from __future__ import annotations

import os
import smtplib
from email.mime.text import MIMEText
from typing import Optional

import structlog
from jinja2 import Environment, FileSystemLoader

log = structlog.get_logger()

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")


def _get_jinja_env() -> Environment:
    return Environment(loader=FileSystemLoader(TEMPLATE_DIR))


def send_alert(
    template_name: str,
    subject: str,
    to_email: str,
    from_email: str,
    smtp_host: str = "localhost",
    smtp_port: int = 25,
    **template_vars,
) -> None:
    env = _get_jinja_env()
    template = env.get_template(template_name)
    body = template.render(**template_vars)

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.send_message(msg)
        log.info("alert.sent", to=to_email, subject=subject)
    except Exception as e:
        log.error("alert.failed", error=str(e))
```

- [ ] **Step 3: Commit**

```bash
git add src/stages/log.py src/lib/alert.py
git commit -m "feat: Stage 8 LOG + email alerting"
```

---

### Task 8: Health Check CLI

**Files:**
- Create: `src/healthcheck.py`

- [ ] **Step 1: Create healthcheck.py**

```python
# src/healthcheck.py
from __future__ import annotations

import argparse
import sys
from datetime import date
from typing import Callable, List, Tuple

import structlog

log = structlog.get_logger()


def check_mysql_connection(config) -> bool:
    from src.lib.db import get_engine
    try:
        engine = get_engine(config)
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception as e:
        log.error("healthcheck.mysql.failed", error=str(e))
        return False


def check_anthropic_ping(config) -> bool:
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=config.anthropic_api_key)
        client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=5,
            messages=[{"role": "user", "content": "ping"}],
        )
        return True
    except Exception as e:
        log.error("healthcheck.anthropic.failed", error=str(e))
        return False


def check_elevenlabs_ping(config) -> bool:
    if not config.elevenlabs_api_key:
        log.warning("healthcheck.elevenlabs.skipped", reason="no API key")
        return True
    try:
        import elevenlabs
        client = elevenlabs.ElevenLabs(api_key=config.elevenlabs_api_key)
        client.voices.get_all()
        return True
    except Exception as e:
        log.error("healthcheck.elevenlabs.failed", error=str(e))
        return False


def check_disk_space() -> bool:
    import shutil
    usage = shutil.disk_usage("/")
    free_gb = usage.free / (1024 ** 3)
    if free_gb < 2.0:
        log.error("healthcheck.disk.low", free_gb=round(free_gb, 1))
        return False
    return True


def check_node_installed() -> bool:
    import subprocess
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except Exception:
        return False


def check_ffmpeg_installed() -> bool:
    import subprocess
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except Exception:
        return False


def check_brief_exists(config, run_date: date) -> bool:
    from src.lib.db import get_engine, get_session
    from src.models import Brief
    engine = get_engine(config)
    session = get_session(engine)
    try:
        brief = session.query(Brief).filter(Brief.date == run_date).first()
        if brief is None:
            log.warning("healthcheck.brief.not_found", date=str(run_date))
            return False
        return True
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description="NewsBrief Health Check")
    parser.add_argument("--infra", action="store_true", help="Run infrastructure checks only")
    parser.add_argument("--content", action="store_true", help="Run content checks only")
    args = parser.parse_args()

    from src.config import load_config
    config = load_config()
    today = date.today()

    results = []

    if args.infra or (not args.infra and not args.content):
        infra_checks: List[Tuple[str, Callable]] = [
            ("MySQL connection", lambda: check_mysql_connection(config)),
            ("Claude API", lambda: check_anthropic_ping(config)),
            ("ElevenLabs API", lambda: check_elevenlabs_ping(config)),
            ("Disk space >2GB", check_disk_space),
            ("Node.js installed", check_node_installed),
            ("FFmpeg installed", check_ffmpeg_installed),
        ]
        for name, fn in infra_checks:
            ok = fn()
            status = "OK" if ok else "FAIL"
            results.append((name, ok))
            print(f"  [{status}] {name}")

    if args.content or (not args.infra and not args.content):
        content_checks: List[Tuple[str, Callable]] = [
            ("Today's brief exists", lambda: check_brief_exists(config, today)),
        ]
        for name, fn in content_checks:
            ok = fn()
            status = "OK" if ok else "FAIL"
            results.append((name, ok))
            print(f"  [{status}] {name}")

    failures = [name for name, ok in results if not ok]
    if failures:
        print(f"\nFAILED: {', '.join(failures)}")
        # Send alert
        from src.lib.alert import send_alert
        if config.alert_email_to:
            send_alert(
                template_name="alert_failure.j2",
                subject=f"[NewsBrief] Healthcheck FAILED - {today}",
                to_email=config.alert_email_to,
                from_email=config.alert_email_from,
                date=str(today),
                failed_stage="healthcheck",
                issue_number="N/A",
                duration="N/A",
                error_message=f"Failed checks: {', '.join(failures)}",
            )
        sys.exit(1)
    else:
        print("\nAll checks passed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add src/healthcheck.py
git commit -m "feat: health check CLI with infra/content split"
```

---

### Task 9: Status CLI

**Files:**
- Create: `src/status.py`

- [ ] **Step 1: Create status.py**

```python
# src/status.py
from __future__ import annotations

import argparse
from datetime import date, timedelta

from sqlalchemy import desc

from src.config import load_config
from src.lib.db import get_engine, get_session
from src.models import VideoRun, VideoUpload


def main():
    parser = argparse.ArgumentParser(description="NewsBrief Pipeline Status")
    parser.add_argument("--date", type=str, help="Show details for a specific date")
    parser.add_argument("--days", type=int, default=7, help="Show last N days (default: 7)")
    args = parser.parse_args()

    config = load_config()
    engine = get_engine(config)
    session = get_session(engine)

    try:
        if args.date:
            run_date = date.fromisoformat(args.date)
            run = session.query(VideoRun).filter(VideoRun.run_date == run_date).first()
            if not run:
                print(f"No run found for {run_date}")
                return

            print(f"\n{'='*60}")
            print(f"Run: {run.id} | Issue #{run.issue_number} | Status: {run.status}")
            print(f"Started: {run.started_at} | Completed: {run.completed_at}")
            print(f"Duration: {run.total_duration_s}s")
            print(f"\nStage Timings:")
            for stage in ["extract", "script", "audio", "spec", "render", "post", "archive"]:
                val = getattr(run, f"stage_{stage}_s", None)
                print(f"  {stage:>10}: {val or 'N/A'}s")

            if run.failed_stage:
                print(f"\nFailed: {run.failed_stage} — {run.error_message}")

            uploads = session.query(VideoUpload).filter(VideoUpload.run_id == run.id).all()
            if uploads:
                print(f"\nUploads ({len(uploads)}):")
                for u in uploads:
                    status_icon = "OK" if u.status == "completed" else "FAIL"
                    print(f"  [{status_icon}] {u.platform:>22} {u.platform_url or u.error_message or ''}")

        else:
            cutoff = date.today() - timedelta(days=args.days)
            runs = (
                session.query(VideoRun)
                .filter(VideoRun.run_date >= cutoff)
                .order_by(desc(VideoRun.run_date))
                .all()
            )

            if not runs:
                print(f"No runs in the last {args.days} days.")
                return

            print(f"\n{'Date':<14} {'Issue':<8} {'Status':<12} {'Duration':<12} {'Uploads'}")
            print("-" * 65)
            for run in runs:
                uploads = session.query(VideoUpload).filter(
                    VideoUpload.run_id == run.id,
                    VideoUpload.status == "completed",
                ).count()
                total = session.query(VideoUpload).filter(VideoUpload.run_id == run.id).count()
                dur = f"{run.total_duration_s}s" if run.total_duration_s else "N/A"
                print(f"{run.run_date}    {run.issue_number:<8} {run.status:<12} {dur:<12} {uploads}/{total}")

    finally:
        session.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add src/status.py
git commit -m "feat: status CLI for pipeline history and run details"
```

---

### Task 10: Wire Everything into run.py

**Files:**
- Modify: `src/run.py` — complete the orchestrator with all stages

This is the final wiring task. Update `src/run.py` to include stages 5-8, the gate check, and alert sending. The full orchestrator flow should now be:

EXTRACT -> SCRIPT -> FORMAT -> AUDIO -> SPEC -> RENDER -> GATE -> POST -> ARCHIVE -> LOG -> ALERT

- [ ] **Step 1: Update run.py with complete pipeline**

The full `run.py` should orchestrate all stages with timing, error handling, and the gate check. Key additions:

- After RENDER: call `check_gate()` with the publish mode and `requires_review` flag
- If gate blocks: send review email via `alert.py`, save run as "blocked", exit
- If gate passes: proceed to POST, ARCHIVE, LOG
- After all stages: send success/failure alert email
- Wrap each stage in try/except for per-stage error recording

- [ ] **Step 2: Run full test suite**

Run: `.venv/bin/pytest tests/ -v`
Expected: All tests pass (~50+ tests)

- [ ] **Step 3: Commit**

```bash
git add src/run.py
git commit -m "feat: complete orchestrator — all stages wired end-to-end"
```

---

### Task 11: Cleanup Script

**Files:**
- Create: `src/cleanup.py`

- [ ] **Step 1: Create cleanup.py**

```python
# src/cleanup.py
"""Monthly cleanup: null remotion_spec JSON older than 90 days, delete old logs."""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import text

from src.config import load_config
from src.lib.db import get_engine, get_session

import structlog

log = structlog.get_logger()


def main():
    config = load_config()
    engine = get_engine(config)
    session = get_session(engine)

    cutoff = date.today() - timedelta(days=90)

    try:
        result = session.execute(
            text("UPDATE video_scripts SET remotion_spec = NULL WHERE created_at < :cutoff AND remotion_spec IS NOT NULL"),
            {"cutoff": cutoff},
        )
        session.commit()
        log.info("cleanup.specs_nulled", count=result.rowcount, cutoff=str(cutoff))
    finally:
        session.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add src/cleanup.py
git commit -m "feat: monthly cleanup script for old remotion specs"
```

---

## Plan D Completion Checklist

After all tasks are done, verify:

- [ ] `src/stages/gate.py` implements preview/gate/auto modes with proper-noun override
- [ ] `src/stages/post.py` uploads to 6 platform endpoints with per-platform failure isolation
- [ ] `src/stages/archive.py` uploads all artifacts to Google Drive date-stamped folder
- [ ] `src/stages/log.py` writes video_runs, video_uploads, video_scripts records
- [ ] `src/lib/platforms/` has clients for YouTube, Facebook, Instagram, LinkedIn, S3, Drive
- [ ] `src/lib/alert.py` sends success/failure emails via SMTP
- [ ] `src/healthcheck.py` runs infra checks (0600) and content checks (0730) separately
- [ ] `src/status.py` shows pipeline history and per-run details
- [ ] `src/cleanup.py` nulls old remotion_spec JSON
- [ ] `src/run.py` orchestrates all stages end-to-end
- [ ] All Jinja2 templates exist with UTM-tagged CTA links
- [ ] All tests pass (~55+ tests total across all plans)

## Full Pipeline Complete

With Plans A-D implemented, the pipeline runs:

```
[0800 ET Cron] -> python src/run.py
  Stage 1: EXTRACT  (read DB, assert date)
  Stage 2: SCRIPT   (Claude Sonnet, slot structure)
  Stage 2b: FORMAT  (canonical numbers -> speech)
  Stage 3: AUDIO    (ElevenLabs x5, SSML, proper-noun gate)
  Stage 4: SPEC     (Remotion JSON)
  Stage 5: RENDER   (Remotion subprocess -> 8 outputs + captions)
  Stage 5b: GATE    (publish mode check)
  Stage 6: POST     (6 platform uploads)
  Stage 7: ARCHIVE  (Google Drive)
  Stage 8: LOG      (MySQL + email alert)
```
