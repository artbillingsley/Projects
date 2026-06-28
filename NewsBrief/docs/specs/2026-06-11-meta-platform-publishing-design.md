# Meta Platform Publishing Design (v2)

**Date:** 2026-06-11 (revised)
**Status:** Approved
**Scope:** Add Instagram Reels and Facebook Reels to the pipeline (Phase 1), then Threads (Phase 2)
**Supersedes:** Original v1 of this document. Also supersedes the 16:9 anchor distribution paths from earlier design docs — the pipeline now renders 9:16 only (decision 2026-06-11).

## Critical Path: Meta App Review (start immediately)

`instagram_content_publish` (or its current name `instagram_business_content_publish` — verify against live docs) requires **Advanced Access** via Meta App Review. This involves:

- Business verification (business docs, domain verification)
- Screencast demonstrating the use case
- Review period: **2–4 weeks per submission**

`threads_content_publish` requires separate Threads API access approval from Meta.

**Action:** Submit App Review requests for Instagram and Threads in parallel with the build. Code cannot publish until these clear. Facebook Page posting with Standard Access may work without review for pages you admin — verify.

## Phase 1: Facebook Reels + Instagram Reels

### Token Architecture

Facebook and Instagram share one token chain. **Threads is a separate auth subsystem** (see Phase 2).

```
Meta Developer App
  → Facebook Login (browser, short-lived user token)
  → Exchange for long-lived user token (60 days)
  → Exchange for Page Access Token (never expires)
  → Covers: Facebook Page + Instagram Business Account
```

**Required permissions (verify current scope names against live 2026 docs):**
- `pages_manage_posts` — post to Facebook Page
- `pages_read_engagement` — read page metadata
- `instagram_basic` — access Instagram account info
- `instagram_business_content_publish` — publish Reels to Instagram (was `instagram_content_publish`, may have been renamed)

### Components

#### 1. `meta_auth.py` (new, local script)

One-time local OAuth script for Facebook + Instagram:
- Opens browser for Facebook Login with required permissions
- Exchanges short-lived token → long-lived user token → permanent page token
- Fetches Instagram Business Account ID linked to the page
- Outputs: `FACEBOOK_ACCESS_TOKEN`, `FACEBOOK_PAGE_ID`, `INSTAGRAM_ACCOUNT_ID`
- Does NOT handle Threads (separate script)

#### 2. `src/lib/platforms/instagram.py` (rewrite)

Replace `video_url`-based upload with resumable direct upload. Key implementation detail: the binary upload goes to `rupload.facebook.com`, not the Graph API host.

1. `POST graph.facebook.com/{ig_account_id}/media` with `media_type=REELS`, `upload_type=resumable` → returns container `id`
2. `PUT` raw video binary to `rupload.facebook.com/ig-api-upload/{api-version}/{container_id}` with headers: `Authorization: OAuth {token}`, `offset: 0`, `file_size: {bytes}`
3. Poll `GET /{container_id}?fields=status_code` until `FINISHED` (10s intervals, 300s timeout)
4. `POST /{ig_account_id}/media_publish` with `creation_id={container_id}`

Function signature changes from `video_url: str` to `file_path: str`. Remove `s3_client`/`boto3` dependency from `_upload_instagram_reel` in post.py.

**Note:** Instagram Graph API caps Reels at ~90 seconds via API even though the consumer app allows longer. Current daily brief runs ~2:26 — verify whether this is enforced. If so, the brief may need trimming or Instagram gets a micro-clip instead.

#### 3. `src/lib/platforms/facebook.py` (no changes)

Already supports direct file upload for `upload_reel`. No modifications needed.

#### 4. `src/stages/post.py` (update)

- Rewrite `_upload_instagram_reel` to use direct upload (remove S3/boto3)
- Remove `_upload_facebook_video` (16:9 path, no longer needed)
- Keep `_upload_facebook_reel` as-is

#### 5. `src/config.py` (minor update)

Fields `facebook_page_id`, `facebook_access_token`, `instagram_account_id` already exist. Remove `instagram_access_token` (uses the same page token). No new fields for Phase 1.

### Captions

**No hardcoded strings.** Captions must reflect the brand voice established throughout the project:

- **Never use "AI-curated"** — the brand thesis is human judgment, sourced reasoning, and Commander-grade authority. "AI-curated" commoditizes the product against auto-generated news feeds and undermines trust on political content.
- Captions should be generated in the script stage via `platform_meta` in the spec, or built dynamically from spec data (as the LinkedIn caption builder already does).
- **Instagram:** No clickable links in captions. CTA routes through link-in-bio. Hashtags for discoverability.
- **Facebook Reel:** Can include links. YouTube Short URL injected dynamically (same pattern as LinkedIn).
- **Sign-off:** Use "Decide." consistent with the Close slot.

Example caption structure (dynamically built from spec):
```
COGNOSCERE Daily Brief — {date}

{headline_bullets}

Sources: {source_names}

Decide.

#news #COGNOSCERE #dailybrief
```

YouTube Short URL injected into Facebook caption (where links work), omitted from Instagram caption (where links don't).

### Pipeline Order

```
render 9:16 → youtube_short → linkedin_video → facebook_reel → instagram_reel
```

YouTube uploads first so the Short URL is available for Facebook and LinkedIn captions.

### Env Vars (EC2 `.env`)

```
FACEBOOK_ACCESS_TOKEN=<permanent page token>
FACEBOOK_PAGE_ID=343042179087985
INSTAGRAM_ACCOUNT_ID=17841401458245652
PUBLISH_PLATFORMS=youtube_short,linkedin_video,facebook_reel,instagram_reel
```

## Phase 2: Threads (deferred, separate auth)

Threads is a **separate auth subsystem** with its own OAuth flow, token lifecycle, and API host.

### Why Deferred

1. **Threads API approval** is a separate submission from Instagram — needs its own App Review
2. **Upload mechanism unverified** — Threads may still require `video_url` (public URL) rather than supporting resumable upload. If so, a presigned URL path is needed (minimal S3 bucket, or host on cognoscerellc.com)
3. **Separate token** — Threads tokens expire at 60 days and must be refreshed, unlike the permanent Facebook Page token

### Threads Auth Architecture (when ready)

```
Threads OAuth (graph.threads.net)
  → Authorization code flow via Instagram identity
  → Scopes: threads_basic, threads_content_publish
  → Long-lived token (60 days)
  → Must be refreshed via /refresh_access_token before expiry
```

- `threads_auth.py` — separate local OAuth script hitting `graph.threads.net`
- `THREADS_ACCESS_TOKEN` — separate env var (not the Facebook page token)
- `THREADS_USER_ID` — fetched from `GET /me` on the Threads API (NOT the Instagram account ID)
- Refresh job: extend healthcheck to auto-refresh Threads token when <7 days from expiry

### Threads Upload (verify before building)

Check live Threads docs for whether resumable upload is supported:
- **If resumable:** Same pattern as Instagram rewrite (direct upload)
- **If video_url only:** Options are (a) minimal S3 presigned URL path for Threads only, (b) host clip at cognoscerellc.com, (c) wait for resumable support

### Threads Captions

Short-form text + YouTube Shorts link (Threads favors concise posts):
```
COGNOSCERE Daily Brief — {date}

{lead_headline}
+ {scan_count} more stories

Watch: {youtube_short_url}

Decide.
```

## Token Health (both phases)

Extend the 10:00 UTC infra healthcheck to validate Meta tokens:

- Call `GET /debug_token?input_token={token}` to check validity and expiry
- For Threads (Phase 2): auto-refresh long-lived token when <7 days from expiry via `GET /refresh_access_token`
- Alert on invalid/expiring tokens before the 12:00 UTC pipeline run

## Manual Setup Steps

### Phase 1 (do now)
1. Create Meta Developer App at developers.facebook.com (type: Business)
2. Add "Facebook Login for Business" product
3. **Submit App Review** for `instagram_business_content_publish` with screencast — this is the critical path
4. Complete business verification if not already done
5. While waiting for review: build code, test with Standard Access on owned Page
6. Once approved: run `meta_auth.py` locally, set env vars on EC2

### Phase 2 (after Phase 1 ships)
1. Apply for Threads API access
2. Verify Threads upload mechanism (resumable vs video_url)
3. Build `threads_auth.py` and `threads.py`
4. Add token refresh to healthcheck
