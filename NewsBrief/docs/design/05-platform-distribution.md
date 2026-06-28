# Section 5: Platform Distribution & Upload

## Target Platforms

| Platform | API | Auth Method | Key Constraints |
|----------|-----|-------------|-----------------|
| YouTube | YouTube Data API v3 | OAuth2 refresh token | 10,000 daily quota units; 1 upload = 1,600 units (~6 uploads/day) |
| Facebook | Graph API v19+ | Long-lived Page Access Token | Resumable upload for >1GB. Reels via /me/video_reels |
| Instagram Reels | Instagram Graph API | Same token as Facebook (linked Page + IG Business Account) | 90s max. Async upload: create container -> poll -> publish |
| LinkedIn | LinkedIn Marketing API | OAuth2 3-legged refresh token | 200MB max per video. registerUpload -> PUT binary -> create post |

## Credential Management

All credentials in `/home/ec2-user/newsbrief/.env`:

```bash
# YouTube
YOUTUBE_CLIENT_ID=...
YOUTUBE_CLIENT_SECRET=...
YOUTUBE_REFRESH_TOKEN=...
YOUTUBE_CHANNEL_ID=...

# Facebook / Instagram
FB_PAGE_ID=...
FB_PAGE_ACCESS_TOKEN=...          # Long-lived (60-day), auto-refreshed
IG_BUSINESS_ACCOUNT_ID=...

# LinkedIn
LINKEDIN_CLIENT_ID=...
LINKEDIN_CLIENT_SECRET=...
LINKEDIN_REFRESH_TOKEN=...
LINKEDIN_ORG_ID=...               # Company page URN

# Google Drive
GDRIVE_SERVICE_ACCOUNT_KEY=./config/gdrive-sa-key.json
GDRIVE_FOLDER_ID=...

# ElevenLabs
ELEVENLABS_API_KEY=...
ELEVENLABS_VOICE_ID=...

# Claude API
ANTHROPIC_API_KEY=...
```

### Token Refresh Strategy

| Platform | Token Lifetime | Refresh Strategy | Manual Re-auth |
|----------|---------------|-----------------|----------------|
| YouTube | Long-lived refresh token | google-auth auto-refresh | Rarely needed |
| Facebook/IG | 60-day page token | Auto-refresh on each run | ~6x/year if refresh fails (R12) |
| LinkedIn | 365-day refresh token | Auto-refresh on each run | Annual |

If any auth fails, that platform's upload is skipped. Others proceed. Auth failures trigger email alerts.

**R12 note:** Meta's 60-day page token does not auto-refresh indefinitely without conditions. Budget for periodic manual re-auth (~6 times per year). The alerting system catches these; the operator re-authenticates via the Graph Explorer flow.

## Daily Upload Matrix

| Platform | Content | File | Aspect | Caption Style |
|----------|---------|------|--------|--------------|
| YouTube (video) | Full anchor brief | anchor-16x9.mp4 | 16:9 | Detailed description, all stories, links, tags |
| YouTube (Short) | Lead story clip | clip-C1-*-9x16.mp4 | 9:16 | Short hook + "Full brief on our channel" |
| Facebook (feed) | Full anchor brief | anchor-16x9.mp4 | 16:9 | "Today in One Breath" + story list + CTA |
| Facebook (Reel) | Best mass-appeal clip | clip-C*-9x16.mp4 | 9:16 | Punchy hook + "Full brief linked below" |
| Instagram (Reel) | Best mass-appeal clip | clip-C*-9x16.mp4 | 9:16 | Hook + 5-8 hashtags + CTA in bio |
| LinkedIn (video) | Full anchor brief | anchor-16x9.mp4 | 16:9 | WHY IT MATTERS synthesis + professional CTA |

**Total daily uploads: 6**

## Platform-Specific Details

### YouTube

Two uploads: anchor video (regular) + lead clip (Short).

YouTube description template:
```
COGNOSCERE Daily Brief -- {date} | Issue #{brief_id}

{today_in_one_breath}

STORIES COVERED:
{lead_headline} [{lead_cif_tag}]
{scan_items_formatted}

---
Every source cited. Every claim tagged. Read the full record:
https://www.cognoscerellc.com/news/{date_slug}/?utm_source=youtube&utm_medium=video&utm_campaign=cdb-{date_slug}&utm_content=anchor

Subscribe to the daily email: https://cognoscerellc.substack.com/?utm_source=youtube&utm_medium=video&utm_campaign=cdb-{date_slug}&utm_content=anchor
CIFaaS intelligence platform: https://cifaas.cognoscerellc.com/?utm_source=youtube&utm_medium=video&utm_campaign=cdb-{date_slug}&utm_content=anchor

COGNOSCERE LLC | A Service-Disabled Veteran-Owned Small Business
Green Cove Springs, Florida

#DailyBrief #Intelligence #News #COGNOSCERE
```

Custom thumbnail uploaded via `thumbnails().set()` API.

### Facebook

Two uploads: page video (feed) + one Reel.

Reel selection: lead story clip (C1) by default, unless LLM flagged a SCAN item with higher mass-market appeal. Selection encoded in Remotion spec at Stage 2.

### Instagram Reels

One upload per day. Async three-step flow:
1. Upload clip to S3/R2 transient bucket, generate presigned URL (15-min expiry)
2. Create IG container with presigned URL as `video_url`
3. Poll until status = FINISHED
4. Publish
5. (Presigned URL auto-expires; no cleanup needed)

**Upload URL (amended per R5):** Uses a presigned S3 or Cloudflare R2 URL instead of a public Google Drive link. Drive does not serve raw video bytes for files >25MB (returns HTML interstitial), which would cause the IG Graph API to reject the container. Presigned URLs are direct, private, and auto-expiring. Cost: ~$0.02/month.

**Captions:** Instagram does not support separate caption tracks for Reels. Captions are burned into the video during Remotion render (styled text overlay, bottom-center). Instagram-targeted renders include burned-in captions (R9).

### LinkedIn

One upload per day. Anchor video (16:9). Three-step: registerUpload -> PUT binary -> create post.

Caption style: more professional/analytical. Lead with WHY IT MATTERS synthesis. 3 hashtags max.

## Caption & Metadata Generation

LLM generates platform-specific captions during Stage 2. Stored in spec:

```json
{
  "platform_meta": {
    "youtube_title": "COGNOSCERE Daily Brief - June 10, 2026 | Iran Strikes, Immigration Bill, Gas Prices",
    "youtube_description": "...",
    "youtube_tags": ["news", "intelligence", "Iran", "Hormuz", "daily brief"],
    "youtube_short_title": "U.S. helicopter down near Hormuz #news #shorts",
    "facebook_caption": "Today in One Breath: ...",
    "facebook_reel_caption": "The war near Hormuz is already at your pump...",
    "instagram_caption": "An American helicopter is down...\n\n#DailyBrief #COGNOSCERE...",
    "linkedin_caption": "Here is the thread: The war near Hormuz..."
  }
}
```

## Upload Sequencing

YouTube first (most forgiving API), then Facebook, then LinkedIn, then Instagram (most fragile).

```
YouTube Video -> YouTube Short -> Facebook Video -> Facebook Reel
                                                        |
                                                        v
                                   LinkedIn Video  Instagram Reel
```

Each platform upload is independent. One failure does not block others.

## Run Logging

Per-platform success/failure logged to `video_runs` table:

```json
{
  "run_id": "vr-2026-06-10",
  "brief_id": "N103",
  "started_at": "2026-06-10T12:00:00Z",
  "completed_at": "2026-06-10T12:08:43Z",
  "stages": {
    "extract": {"status": "ok", "duration_s": 1.2},
    "script": {"status": "ok", "duration_s": 8.4},
    "audio": {"status": "ok", "duration_s": 12.1},
    "render": {"status": "ok", "duration_s": 247.6},
    "upload": {
      "youtube_video": {"status": "ok", "video_id": "abc123"},
      "youtube_short": {"status": "ok", "video_id": "def456"},
      "facebook_video": {"status": "ok", "post_id": "789"},
      "facebook_reel": {"status": "ok", "post_id": "012"},
      "instagram_reel": {"status": "FAILED", "error": "Container stuck in PROCESSING"},
      "linkedin_video": {"status": "ok", "post_urn": "..."}
    },
    "archive": {"status": "ok", "drive_folder_url": "..."}
  },
  "total_duration_s": 523
}
```

## Alerting

Post-run summary email (via SES or existing SMTP) to operator. Green/red per platform. Failed uploads include error + local file path for manual upload.

## Rate Limits & Quotas

| Platform | Daily Limit | Our Usage | Headroom |
|----------|-------------|-----------|----------|
| YouTube | 10,000 quota units | ~3,200 (2 uploads) | Comfortable |
| Facebook | 250 API calls/hour | ~20 calls | Comfortable |
| Instagram | 25 Reels/day | 1 | Comfortable |
| LinkedIn | 100 API calls/day | ~10 calls | Comfortable |
| ElevenLabs | Plan-dependent | ~2 min/day = ~60 min/mo | Creator plan minimum ($22/mo) |
| Claude API | Token-based billing | ~4K in + ~2K out per run | Comfortable |

**ElevenLabs is the binding constraint.** Creator plan ($22/mo, 2 hours) is minimum. Pro plan ($99/mo, 4 hours) recommended.
