# Section 8: Dependencies & Setup

## 8.1 Python Dependencies

```
# requirements.txt

# Database
SQLAlchemy>=2.0
PyMySQL>=1.1
cryptography>=42.0

# AI / LLM
anthropic>=0.40

# Audio
elevenlabs>=1.0
pydub>=0.25

# Video post-processing
ffmpeg-python>=0.2

# Platform uploads
google-api-python-client>=2.100
google-auth>=2.20
google-auth-oauthlib>=1.2
google-auth-httplib2>=0.2
requests>=2.31
boto3>=1.34                        # S3/R2 presigned URLs for Instagram uploads (R5)

# Configuration
python-dotenv>=1.0
PyYAML>=6.0

# Observability
structlog>=24.0

# Utilities
jinja2>=3.1
python-dateutil>=2.9
```

## 8.2 Node.js / Remotion Dependencies

```json
{
  "name": "newsbrief-renderer",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "render": "remotion render",
    "preview": "remotion preview",
    "upgrade": "remotion upgrade"
  },
  "dependencies": {
    "remotion": "^4.0",
    "@remotion/cli": "^4.0",
    "@remotion/media-utils": "^4.0",
    "react": "^18.2",
    "react-dom": "^18.2",
    "zod": "^3.22"
  },
  "devDependencies": {
    "typescript": "^5.3",
    "@types/react": "^18.2",
    "prettier": "^3.1"
  }
}
```

## 8.3 System-Level Dependencies (EC2)

```bash
# Already present (from CDB pipeline)
python3.11+
pip / venv
mysql-client

# New requirements
node 20 LTS         # Remotion requires Node 18+
npm
ffmpeg 6+
chromium-headless    # Remotion rendering engine
```

## 8.4 EC2 Provisioning Checklist

### Phase 1: System Packages

```bash
# Node.js 20 LTS (Amazon Linux 2023)
curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
sudo yum install -y nodejs

# FFmpeg
sudo yum install -y ffmpeg

# Chromium dependencies (for Remotion headless rendering)
sudo yum install -y \
  alsa-lib atk cups-libs gtk3 libXcomposite libXdamage libXrandr \
  mesa-libgbm pango nss libdrm

# Verify
node --version      # v20.x
npm --version       # 10.x
ffmpeg -version     # 6.x+
```

### Phase 2: Python Environment

```bash
cd /home/ec2-user
mkdir newsbrief && cd newsbrief
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Phase 3: Remotion Setup

```bash
cd /home/ec2-user/newsbrief/newsbrief-renderer
npm install
npx remotion --version
npx remotion browser ensure    # Download Chromium (one-time)
```

### Phase 4: Configuration Files

```
/home/ec2-user/newsbrief/
  .env                              # All credentials
  config/
    pronunciation.yaml              # SSML pronunciation dictionary
    gdrive-sa-key.json              # Google Drive service account key
  newsbrief-renderer/               # Remotion project (Node)
    package.json
    src/
  src/                              # Python pipeline source
    run.py                          # Main entry point
    status.py                       # Status checker
    healthcheck.py                  # Pre-flight health check
    stages/
      extract.py
      script.py
      format_speech.py              # Deterministic number-to-speech formatting (R2)
      audio.py
      spec.py
      render.py
      gate.py                       # Publish gate logic (R1)
      post.py
      archive.py
      log.py
    lib/
      db.py                         # Database connection
      elevenlabs.py                 # ElevenLabs client
      pronunciation.py              # SSML injection + proper-noun gate (R8)
      captions.py                   # SRT/VTT generation from timestamps (R9)
      platforms/
        youtube.py
        facebook.py
        instagram.py
        linkedin.py
        drive.py
        s3.py                       # S3/R2 presigned URLs for IG uploads (R5)
    templates/
      youtube_description.j2        # Jinja2 caption templates (UTM-tagged, R4)
      linkedin_caption.j2
      alert_success.j2
      alert_failure.j2
      gate_review.j2                # Review email for publish gate (R1)
  logs/
  tmp/
```

### Phase 5: API Account Setup

| Service | Steps | Credential |
|---------|-------|------------|
| YouTube | 1. Google Cloud project. 2. Enable YouTube Data API v3. 3. OAuth2 credentials (desktop). 4. Initial auth flow for refresh token. | YOUTUBE_REFRESH_TOKEN |
| Facebook | 1. Create Facebook App (Business). 2. Add Pages API + Video Upload. 3. Long-lived Page Access Token via Graph Explorer. | FB_PAGE_ACCESS_TOKEN |
| Instagram | 1. Link IG Business to FB Page. 2. Add IG Graph API permissions. 3. Same token as Facebook. | IG_BUSINESS_ACCOUNT_ID |
| LinkedIn | 1. Create app at Developer Portal. 2. Request Marketing Developer Platform. 3. w_organization_social permission. 4. 3-legged OAuth for refresh token. | LINKEDIN_REFRESH_TOKEN |
| Google Drive | 1. Service account in Cloud Console. 2. Download JSON key. 3. Share Drive folder with SA email. | gdrive-sa-key.json |
| S3 or R2 | 1. Create bucket (private). 2. IAM user with PutObject + presigned URL permissions. 3. Store credentials in .env. | S3_BUCKET, S3_ACCESS_KEY, S3_SECRET_KEY |
| ElevenLabs | 1. Creator or Pro plan. 2. Clone voice. 3. Copy API key + voice ID. | ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID |
| Claude API | 1. API key from Anthropic Console. | ANTHROPIC_API_KEY |

### Phase 6: Cron Setup

```bash
# Set timezone to Eastern (handles EST/EDT automatically)
sudo timedatectl set-timezone America/New_York

# Edit crontab
crontab -e

# Infra health check at 0600 ET (R6)
0 6 * * * cd /home/ec2-user/newsbrief && .venv/bin/python src/healthcheck.py --infra >> logs/healthcheck-$(date +\%Y-\%m-\%d).log 2>&1

# Content health check at 0730 ET (after CDB pipeline completes, R6)
30 7 * * * cd /home/ec2-user/newsbrief && .venv/bin/python src/healthcheck.py --content >> logs/healthcheck-$(date +\%Y-\%m-\%d).log 2>&1

# Pipeline at 0800 ET
0 8 * * * cd /home/ec2-user/newsbrief && .venv/bin/python src/run.py >> logs/newsbrief-$(date +\%Y-\%m-\%d).log 2>&1

# Log cleanup (monthly)
0 0 1 * * find /home/ec2-user/newsbrief/logs -name "*.log" -mtime +30 -delete

# Spec cleanup (monthly)
0 0 1 * * cd /home/ec2-user/newsbrief && .venv/bin/python src/cleanup.py
```

### Phase 7: Verification

```bash
# 1. Database connection
python -c "from src.lib.db import get_connection; print('DB OK')"

# 2. ElevenLabs
python -c "from src.lib.elevenlabs import test_ping; test_ping()"

# 3. Claude API
python -c "import anthropic; c = anthropic.Anthropic(); print('Claude OK')"

# 4. Remotion render
cd newsbrief-renderer && npx remotion render src/Root.tsx Thumbnail --props='{"test":true}' --output=/tmp/test.png

# 5. YouTube auth
python -c "from src.lib.platforms.youtube import test_auth; test_auth()"

# 6. S3/R2 presigned URL test
python -c "from src.lib.platforms.s3 import test_presigned; test_presigned()"

# 7. Preview mode (no uploads)
python src/run.py --date $(date +%Y-%m-%d) --preview

# 8. First live run (in PUBLISH_MODE=preview, requires --approve)
python src/run.py --date $(date +%Y-%m-%d)
```

### Phase 7b: Render Benchmark (R3 — Pre-Launch Blocker)

Before committing to the cost model, benchmark Remotion on the target instance:

```bash
# Render a 2-min 1080p/30fps test composition
time npx remotion render src/Root.tsx AnchorBrief \
  --props='./test/benchmark-spec.json' \
  --output=/tmp/benchmark-16x9.mp4 \
  --width=1920 --height=1080 --fps=30

# Monitor peak memory during render
# (run in a second terminal)
watch -n 1 free -m
```

**Success criteria:**
- Wall-clock render time < 10 min for full 8-output suite
- Peak memory < 3.5GB (leaves headroom on 4GB t3.medium)
- No burst credit exhaustion visible in CloudWatch

**If t3.medium fails:** Upgrade to t3.large (8GB, ~$30/mo) or c6i.large (compute-optimized). Update D3 and D51.

### Phase 7c: Platform Limits Verification (R7)

Confirm against live API docs at build time:

| Check | Expected | Verified | Date |
|-------|----------|----------|------|
| Remotion output codec | H.264 video + AAC audio | [ ] | |
| YouTube upload limit | 128GB, 12hr | [ ] | |
| Facebook Reels max duration (API) | Confirm current limit | [ ] | |
| IG Reels max duration (Graph API) | ~90s (API path, not app) | [ ] | |
| IG Reels file format | MP4, H.264, AAC, 9:16 | [ ] | |
| LinkedIn video max size | 200MB | [ ] | |
| LinkedIn video codec | H.264/AAC | [ ] | |

## 8.5 Estimated Monthly Costs

| Service | Usage | Monthly Cost |
|---------|-------|-------------|
| ElevenLabs | Creator plan (2hr/mo) | $22 |
| Claude API (claude-sonnet-4-20250514) | ~6K tokens/day x 30 | ~$3-5 |
| EC2 (incremental) | Possible upgrade to t3.large pending R3 benchmark | $0-30 |
| S3/R2 transient bucket | ~200MB/day transient, auto-expiring | ~$0.02 |
| RDS (incremental) | 4 new tables, minimal storage | ~$0 |
| Google Drive | Already have 4TB | $0 |
| YouTube/Facebook/IG/LinkedIn APIs | Free tiers | $0 |
| **Total incremental** | | **~$25-57/month** |

**Note (R3):** The $0 EC2 line depends on the render benchmark. If t3.medium cannot handle Remotion rendering, budget $30/mo for a t3.large. The cost range reflects this uncertainty.
