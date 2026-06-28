# COGNOSCERE Daily Video Brief — Project Overview

**Project:** NewsBrief — Automated daily 2-minute news video briefing
**Owner:** COGNOSCERE LLC
**Status:** Design phase
**Created:** 2026-06-10

## Purpose

Automated pipeline that transforms the COGNOSCERE Daily News Brief (CDB) into a 2-minute audio/visual news briefing, plus derived micro-clips, for multi-platform distribution.

## Strategic Goals (Priority Order)

1. **Brand awareness** — Get COGNOSCERE in front of people who don't yet read the CDB, using video platforms as top-of-funnel discovery
2. **Product interest** — Drive interest in intelligence and news products (CIFaaS, Substack, daily email, advisory)
3. **Authority positioning** — Establish a recurring voice presence that positions COGNOSCERE as a credible intelligence source

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Voice | ElevenLabs clone (user's voice) | Anchor credibility without daily studio time |
| Visual style | Kinetic typography (text-driven motion graphics) | Carries credibility without talking head; automatable; works sound-off |
| Render engine | Remotion (React/TypeScript) | Best motion graphics quality for programmatic video; professional easing and animation |
| Orchestrator | Python | Consistent with CDB pipeline stack; handles data, LLM, audio, uploads |
| Pipeline trigger | Cron at 0800 Eastern (wall-clock) | Fixed daily cadence for audience consistency |
| Infrastructure | Same EC2 as CDB pipeline | No resource contention — CDB cron (11 UTC) and video cron (12 UTC EDT) are temporally separated |
| Storage/archive | Google Drive (4TB available) | No additional AWS cost; human-reviewable folder structure |
| Data source | MySQL RDS (`cdb` database, `clusters` table) | Structured data, no parsing needed |
| Distribution | Fully automated via platform APIs | YouTube, Facebook, Instagram Reels, LinkedIn |
| Sign-off | "Decide." | Ties to CIFaaS "tracked, attributable decisions" brand positioning |

## Target Platforms

| Platform | Content | Aspect |
|----------|---------|--------|
| YouTube (video) | Full 2-min anchor brief | 16:9 |
| YouTube (Short) | Lead story micro-clip | 9:16 |
| Facebook (feed) | Full 2-min anchor brief | 16:9 |
| Facebook (Reel) | Best mass-appeal micro-clip | 9:16 |
| Instagram (Reel) | Best mass-appeal micro-clip | 9:16 |
| LinkedIn (video) | Full 2-min anchor brief | 16:9 |

## Architecture Summary

```
[0800 ET Cron] -> Python Orchestrator
                    |
                    +-- Stage 1: EXTRACT  -- Read clusters + ASSERT brief.date == run_date (R6)
                    +-- Stage 2: SCRIPT   -- LLM generates script (claude-sonnet-4-20250514)
                    +-- Stage 2b: FORMAT  -- Deterministic number-to-speech formatting (R2)
                    +-- Stage 3: AUDIO    -- ElevenLabs + SSML + proper-noun gate check (R8)
                    +-- Stage 4: SPEC     -- Build Remotion input JSON
                    +-- Stage 5: RENDER   -- Remotion produces videos + SRT/VTT captions (R9)
                    +-- Stage 5b: GATE    -- Publish gate per PUBLISH_MODE (R1)
                    +-- Stage 6: POST     -- Upload to platforms (presigned S3/R2 for IG) (R5)
                    +-- Stage 7: ARCHIVE  -- All artifacts to Google Drive
                    +-- Stage 8: LOG      -- Write run record to video_runs table
```

## Estimated Monthly Cost

~$25-57/month incremental (ElevenLabs Creator $22 + Claude API ~$3-5 + S3/R2 ~$0.02 + possible EC2 upgrade ~$30 pending R3 benchmark). All platform APIs free tier.

## Related Documents

- [Section 1: System Architecture](./01-system-architecture.md)
- [Section 2: Content Selection & Script Generation](./02-content-script-generation.md)
- [Section 3: Audio Generation & Timestamp Sync](./03-audio-generation.md)
- [Section 4: Remotion Visual Design](./04-visual-design.md)
- [Section 5: Platform Distribution & Upload](./05-platform-distribution.md)
- [Section 6: Database Schema](./06-database-schema.md)
- [Section 7: Error Handling & Monitoring](./07-error-handling-monitoring.md)
- [Section 8: Dependencies & Setup](./08-dependencies-setup.md)
- [Section 9: Design Review Assessment](./09-review-assessment.md)
- [Key Decisions Log](./decisions-log.md)
