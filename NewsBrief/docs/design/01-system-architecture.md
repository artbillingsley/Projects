# Section 1: System Architecture

## Pipeline (Two Runtimes, Cron Trigger, Publish Gate)

```
[0800 ET Cron] -> Python Orchestrator
                    |
                    +-- Stage 1: EXTRACT  -- Read clusters + ASSERT brief.date == run_date
                    +-- Stage 2: SCRIPT   -- LLM generates script (canonical numbers, claude-sonnet-4-20250514)
                    +-- Stage 2b: FORMAT  -- Deterministic number-to-speech formatting
                    +-- Stage 3: AUDIO    -- ElevenLabs + SSML + proper-noun gate check
                    +-- Stage 4: SPEC     -- Build Remotion input JSON (text, timings, story metadata)
                    +-- Stage 5: RENDER   -- Remotion produces videos + SRT/VTT captions
                    +-- Stage 5b: GATE    -- If PUBLISH_MODE != auto, email preview + await approval
                    +-- Stage 6: POST     -- Upload to platforms (presigned S3/R2 URL for IG)
                    +-- Stage 7: ARCHIVE  -- All artifacts to Google Drive (date-stamped folder)
                    +-- Stage 8: LOG      -- Write run record to video_runs table
```

## Key Design Decisions

- **Python orchestrator is the single entry point** — calls Remotion via `subprocess` with a JSON file as input
- **ElevenLabs word-level timestamps drive all text animation timing** — visuals sync to voice, not the other way around
- **Two render passes:** 16:9 (YouTube, Facebook, LinkedIn) and 9:16 (Instagram Reels) from the same Remotion composition
- **All intermediate artifacts** (script, audio, JSON spec, rendered video) written to a working directory, then archived to Google Drive
- **The `video_runs` table** provides the same audit trail the CDB pipeline has via `runs`

## Infrastructure

- **Runtime:** Same EC2 instance as CDB pipeline
- **Database:** Same RDS MySQL (`cdb` schema)
- **Cron:** 0800 Eastern wall-clock (shifts between 1200 and 1300 UTC with daylight savings)
- **Temporal separation:** CDB cron fires at 11 UTC; video cron fires at 12 UTC (EDT) — no resource contention
- **Instance requirement:** t3.medium minimum; benchmark required before launch (R3). Likely upgrade to t3.large or c6i.large (~$30/mo) for Remotion/Chromium rendering.
- **Transient media bucket:** S3 or Cloudflare R2 for Instagram upload URLs (presigned, 15-min expiry). Drive remains archive (R5).
- **Publish mode:** `PUBLISH_MODE` env var controls gate behavior: `preview` (manual approval), `gate` (auto-publish unless vetoed), `auto` (fully hands-off). See Section 9 for phased rollout plan (R1).
- **Health checks:** Infra checks at 0600 ET, content checks at 0730 ET (after CDB completion) (R6)

## Google Drive Archive

- **Auth:** Google Service Account (not OAuth2 user flow) — permanent credential, no token refresh headaches
- **Shared folder:** Target Drive folder shared with service account email

### Folder Structure

```
COGNOSCERE Video Briefs/
  +-- 2026-06-10/
       +-- script.md
       +-- audio.mp3
       +-- remotion-spec.json
       +-- video-16x9.mp4
       +-- video-9x16.mp4
       +-- captions-16x9.srt
       +-- captions-9x16.srt
       +-- thumbnail.png
       +-- run-log.json
```

- Drive upload failure does not block distribution — videos are already posted to platforms by that stage
