# Section 7: Error Handling & Monitoring

## Design Philosophy

Pipeline runs unattended at 0800 ET daily. Error handling must be **self-healing where possible, loudly failing where not, and never silently broken.** A missed day is acceptable. A week of silent failures is not.

## 7.1 Stage-by-Stage Error Handling

### Stage 1: EXTRACT (amended per R6)

| Error | Handling | Severity |
|-------|----------|----------|
| MySQL connection refused | Retry 3x (5s backoff). Abort if down. | CRITICAL |
| No brief found for today | Abort with "no content" status. Do NOT fall back to yesterday's brief. | CRITICAL |
| Brief exists but date != run_date | Abort. "Latest brief is {date}, expected {run_date}. Not publishing stale content." | CRITICAL |
| Brief exists but 0 clusters | Abort. Log "brief has no stories." | CRITICAL |

### Stage 2: SCRIPT (LLM)

| Error | Handling | Severity |
|-------|----------|----------|
| Claude API timeout | Retry 3x (10s, 30s, 60s). | HIGH |
| Claude API rate limit | Wait for reset (response header), retry once. | MEDIUM |
| Malformed JSON returned | Retry with "return valid JSON" appended. Max 2 retries. | HIGH |
| >350 words returned | Log warning. Trim SCAN to 3 items, regenerate SCAN only. | LOW |
| Fewer than 2 stories selected | Abort. | MEDIUM |

### Stage 3: AUDIO (ElevenLabs)

| Error | Handling | Severity |
|-------|----------|----------|
| API down | Retry 3x (5s, 15s, 45s). Abort run. | CRITICAL |
| Single slot fails | Retry slot 3x. Abort full run if still failing. | HIGH |
| Audio >2:15 total | Drop 4th SCAN item. Regenerate SCAN audio. | LOW |
| Timestamps missing | Fall back to estimated timing (count/150 wpm). | MEDIUM |
| Quota exceeded | Abort. Alert immediately. | CRITICAL |
| Pronunciation dictionary missing | Proceed without SSML. Log warning. | MEDIUM |

### Stage 4: SPEC

| Error | Handling | Severity |
|-------|----------|----------|
| JSON serialization error | Code bug. Abort and alert. | CRITICAL |
| Disk write failure | Check disk space. Abort if <1GB free. | CRITICAL |

### Stage 5: RENDER (Remotion)

| Error | Handling | Severity |
|-------|----------|----------|
| Process crash | Retry once. Capture stderr. Abort if repeats. | CRITICAL |
| Timeout >10 min per output | Kill process. Abort remaining. | HIGH |
| Single render fails | Skip that output. Continue others. | MEDIUM |
| Node.js not found | Abort. Provisioning error. | CRITICAL |
| Font files missing | Log warning. Fallback fonts used. | HIGH |
| Out of memory | Render sequentially (not parallel). Retry. | HIGH |

### Stage 5b: GATE (Publish Gate, R1)

| Condition | Handling | Severity |
|-----------|----------|----------|
| PUBLISH_MODE=preview | Email script + preview to operator. Halt. Await `--approve` CLI or timeout. | NORMAL |
| PUBLISH_MODE=gate | Email script at 0700. Auto-publish at 0800 unless `--kill` received. | NORMAL |
| PUBLISH_MODE=auto | Skip gate. Proceed directly to POST. | NORMAL |
| requires_review=true (proper-noun gate, R8) | Override mode: always halt for review, even in auto mode. | HIGH |

### Stage 6: POST (Uploads)

| Error | Handling | Severity |
|-------|----------|----------|
| Auth token expired | Attempt refresh. If fails, skip platform, alert. | HIGH |
| Upload timeout | Retry once (5 min timeout). | MEDIUM |
| Platform 5xx | Retry 2x (30s backoff). Skip if persistent. | MEDIUM |
| Platform 4xx | Do not retry. Log response. Skip. | HIGH |
| IG container stuck PROCESSING | Poll 5 min (10s intervals). Skip if stuck. | MEDIUM |
| Rate limit | Wait for reset. Retry once. | LOW |

### Stage 7: ARCHIVE (Drive)

| Error | Handling | Severity |
|-------|----------|----------|
| Drive auth failure | Skip archive, alert. Non-blocking. | LOW |
| Upload timeout | Retry once. Skip if fails. | LOW |

### Stage 8: LOG

| Error | Handling | Severity |
|-------|----------|----------|
| MySQL write failure | Retry once. Fall back to local JSON. Alert. | MEDIUM |

## 7.2 Retry Strategy

Exponential backoff with jitter:

```python
def retry_with_backoff(fn, max_retries=3, base_delay=5.0, max_delay=120.0):
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as e:
            if attempt == max_retries:
                raise
            delay = min(base_delay * (2 ** attempt), max_delay)
            jitter = random.uniform(0, delay * 0.25)
            time.sleep(delay + jitter)
```

## 7.3 Alerting

**Email alert after every run** via Amazon SES or existing SMTP relay.

### Success Email

```
Subject: [NewsBrief] June 10, 2026 - 6/6 platforms posted

Issue #N103 | Duration: 8m 43s

UPLOADS:
  YouTube (video)    OK  https://youtube.com/watch?v=abc123
  YouTube (Short)    OK  https://youtube.com/shorts/def456
  Facebook (video)   OK  https://fb.com/...
  Facebook (Reel)    OK  https://fb.com/reel/...
  Instagram (Reel)   OK  https://instagram.com/reel/...
  LinkedIn (video)   OK  https://linkedin.com/feed/update/...

COSTS:
  ElevenLabs: 1,842 chars (~$0.05)
  Claude API: 4,200 in / 1,800 out (~$0.08)

ARCHIVE: https://drive.google.com/...
PRONUNCIATION: 2 new words flagged for review
```

### Failure Email

```
Subject: [NewsBrief] FAILED - June 10, 2026 - Stage: AUDIO

Issue #N103 | Failed at: Stage 3 (AUDIO) after 22s

ERROR: ElevenLabs API returned 429 (quota exceeded)

ACTION REQUIRED:
  - Check ElevenLabs quota
  - Manual re-run: python run.py --date 2026-06-10
```

### Alert Config

```bash
ALERT_EMAIL_TO=arthur@cognoscerellc.com
ALERT_EMAIL_FROM=newsbrief@cognoscerellc.com
```

## 7.4 Health Checks (amended per R6)

**Split into two runs** to avoid checking content before the CDB pipeline completes:

**Infra check at 0600 ET** (2 hours before pipeline):

```python
infra_checks = [
    ("MySQL connection",     check_mysql_connection),
    ("ElevenLabs API",       check_elevenlabs_ping),
    ("Claude API",           check_anthropic_ping),
    ("YouTube auth",         check_youtube_token),
    ("Facebook auth",        check_facebook_token),
    ("Instagram auth",       check_instagram_token),
    ("LinkedIn auth",        check_linkedin_token),
    ("Google Drive auth",    check_drive_token),
    ("S3/R2 auth",           check_transient_bucket),
    ("Disk space >2GB",      check_disk_space),
    ("Node.js available",    check_node_installed),
    ("Remotion installed",   check_remotion_installed),
    ("FFmpeg available",     check_ffmpeg_installed),
]
```

**Content check at 0730 ET** (after CDB pipeline completes at ~0700 ET):

```python
content_checks = [
    ("Today's brief exists",        check_brief_exists),
    ("Brief date matches today",    check_brief_date_is_today),
    ("Brief has clusters",          check_brief_has_clusters),
]
```

Failures alert immediately, giving operator time to fix before the 0800 pipeline fires.

## 7.5 Operational Runbook

```bash
# Manual re-run (full)
python src/run.py --date 2026-06-10

# Re-run single stage
python src/run.py --date 2026-06-10 --stage render
python src/run.py --date 2026-06-10 --stage post
python src/run.py --date 2026-06-10 --stage post --platform instagram_reel

# Preview (no uploads, no logging)
python src/run.py --date 2026-06-10 --preview

# Dry run (script only)
python src/run.py --date 2026-06-10 --dry-run

# Force re-run (overwrite existing)
python src/run.py --date 2026-06-10 --force

# Approve a gated run (R1 — publish mode: preview)
python src/run.py --date 2026-06-10 --approve

# Kill a gated run (R1 — publish mode: gate, prevents auto-publish)
python src/run.py --date 2026-06-10 --kill

# Check status
python src/status.py                    # Last 7 runs
python src/status.py --date 2026-06-10  # Detailed breakdown
```

## 7.6 Log Files

```
/home/ec2-user/newsbrief/
  logs/
    newsbrief-2026-06-10.log      # Full pipeline log (DEBUG level)
    healthcheck-2026-06-10.log    # Pre-flight check log
  tmp/
    2026-06-10/                   # Working directory (cleaned after archive)
```

- **Rotation:** Daily files. Keep 30 days locally.
- **Canonical audit trail:** MySQL (video_runs + video_uploads), not log files.
- **Working directory cleanup:** Deleted after successful archive. Preserved on failure for inspection.
