# NewsBrief — Decisions Log

All key design decisions made during the brainstorming phase, with rationale.

## Architecture

| # | Decision | Choice | Alternatives Considered | Rationale |
|---|----------|--------|------------------------|-----------|
| D1 | Pipeline language | Python orchestrator + Remotion (Node) renderer | Pure Python (FFmpeg+Pillow), MoviePy, pure Remotion | Python for data/audio/uploads; Remotion for professional motion graphics. Clean boundary via JSON spec. |
| D2 | Render engine | Remotion (React/TypeScript) | FFmpeg+Pillow, MoviePy | Without talking head, visuals carry 100% of credibility. Need spring animations, professional easing. Remotion built for programmatic video. |
| D3 | Infrastructure | Same EC2 as CDB pipeline | Separate EC2, Lambda, ECS | Cron-based = no concurrent resource contention. t3.medium sufficient. Simplest ops. |
| D4 | Cron schedule | 0800 Eastern wall-clock | Fixed UTC, event-driven | Consistent audience experience. Shifts between 1200-1300 UTC with DST. |
| D5 | Data source | MySQL RDS (cdb.clusters table) | Parse email HTML, Substack API | Structured data already exists. No parsing layer needed. |
| D6 | Artifact storage | Google Drive (4TB) | S3 | No additional cost. Human-reviewable. Service account auth. Migrateable to S3 later. |
| D7 | Distribution | Fully automated API uploads | Manual upload, semi-automated | Maximum hands-off daily operation. Per-platform failure isolation. |

## Content & Script

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| D8 | Script structure | 5 self-contained slots (HOOK/LEAD/SCAN/WHY/CLOSE) | Self-containment rule enables mechanical micro-clip extraction. Write once, emit both. |
| D9 | Word budget | 290-310 words at 150 wpm = 2:00 ceiling | Authoritative pace. 2:00 is ceiling, not quota. |
| D10 | Story selection | LLM (Claude) with DEVELOPING > Impact > Variety > Recency priority | Editorial judgment delegated to LLM with structured criteria. Logged for audit. |
| D11 | Micro-clips | First-class output, not afterthought. 5 clips per day. | 5x distribution surface from single production run. |
| D12 | Sign-off | "Decide." | Ties to CIFaaS "tracked, attributable decisions." One word, ownable. Reserve "Choose." for AMAR. |
| D13 | Number formatting | Spell everything in pipeline | "four-sixteen" not "$4.16." Done programmatically, not by hand. |

## Audio

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| D14 | Voice | ElevenLabs clone (user's voice) | Anchor credibility without daily studio time. |
| D15 | API calls | One per slot (5 per run) | Clean per-slot timing. Micro-clip audio = slot file + CLOSE file. One failure = one re-render. |
| D16 | Pronunciation | SSML dictionary (config/pronunciation.yaml) | Pipeline-injected. Grows over time. Prevents first-time mispronunciation. |
| D17 | Audio post-processing | Loudness normalization (-16 LUFS) + noise gate + trim only | Keep voice natural. No compression/EQ. |
| D18 | Voice settings | Stability 0.65-0.70, Similarity 0.80, Style 0.15-0.20, Speed 0.95 | Tuned once, locked. Variation from script rhythm, not parameter jitter. |
| D19 | Timing sync | Voice is master clock. All visuals driven by word-level timestamps. | Nothing hardcoded. If voice runs long, visuals stretch to match. Professional feel. |

## Visual Design

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| D20 | Background | Dark (#0F1419 near-black) | Standard for news video. Maximum text contrast. Avoids "cheap" pure black. |
| D21 | Accent color | Gold #C9A227 | Carries from CDB email palette. Brand anchor on screen. |
| D22 | Headline font | DM Serif Display | Serif signals editorial authority. Pairs with CDB's Georgia. |
| D23 | Body font | Inter | Matches CDB. Clean, high x-height, screen-optimized. |
| D24 | Data/tag font | JetBrains Mono | Monospace signals "structured data." Reinforces intelligence brand. |
| D25 | Animation | Spring physics everywhere | Springs look intentional. Linear looks robotic. Biggest quality differentiator. |
| D26 | HOOK treatment | No logo, no branding. Just the statement. | Brand earns attention by leading with value. |
| D27 | CLOSE "Decide." | Last word on screen. Alone. Gold. 1.5s hold. | Brand signature. Last thing viewer associates with COGNOSCERE. |
| D28 | Responsive | One composition, two renders (16:9 + 9:16) | Components self-adapt via useVideoConfig(). No separate template maintenance. |

## Platform Distribution

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| D29 | Platforms | YouTube, Facebook, Instagram Reels, LinkedIn | Twitch dropped — target audience not there. |
| D30 | Daily uploads | 6 total (2 YT, 2 FB, 1 IG, 1 LI) | Anchor (16:9) to feed platforms. Best micro-clip (9:16) to short-form platforms. |
| D31 | Upload order | YT -> FB -> LI -> IG | Most forgiving API first. Instagram (fragile async) last. |
| D32 | Failure isolation | Per-platform independent | One failure does not block others. Failed uploads logged + human-alertable. |
| D33 | Instagram URL requirement | Temp public Drive link (~60s) | Simplest approach. File reverted to private after publish. |
| D34 | LinkedIn caption style | WHY IT MATTERS synthesis. 3 hashtags max. | More professional/analytical than other platforms. |
| D35 | ElevenLabs plan | Creator minimum ($22/mo). Pro recommended ($99/mo). | ~60 min/month usage. Creator = 2hr. Pro = 4hr with re-render headroom. |

## Database

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| D36 | Database location | Same RDS MySQL (`cdb` schema) | No new database. Extend existing schema with 4 new tables. |
| D37 | video_uploads table | Normalized (one row per platform per run) | 6 uploads per run with independent success/failure. Can't store as single JSON column if you want to query by platform. |
| D38 | video_scripts table | Separate from video_runs | Avoids bloating audit table with large TEXT/JSON fields. |
| D39 | pronunciation_log table | Persistent tracking of new proper nouns | Flags unrecognized words for human review. Prevents recurring mispronunciation. |
| D40 | Remotion spec retention | Null JSON after 90 days, keep script text indefinitely | Spec JSON is large but only needed for re-renders. Script text is small and valuable for audit. |

## Error Handling & Monitoring

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| D41 | Failure philosophy | Self-healing where possible, loud failure where not | A missed day is acceptable. A week of silent failures is not. |
| D42 | Per-platform isolation | One platform failure does not block others | Partial distribution > no distribution. |
| D43 | Pre-flight health check | **AMENDED (R6):** Split into infra (0600 ET) + content (0730 ET) | Content checks must run after CDB completion. Infra checks stay early. |
| D44 | Alerting | Email after every run (success digest or failure alert) | Operator always knows pipeline status. No silent days. |
| D45 | Manual re-run support | CLI with --date, --stage, --platform, --preview, --dry-run, --force, --approve, --kill flags | Granular recovery + publish gate control (R1). |
| D46 | Retry strategy | Exponential backoff with jitter, max 3 retries | Standard pattern. Jitter prevents thundering herd on shared APIs. |

## Dependencies & Operations

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| D47 | Python logging | structlog (JSON-formatted) | Structured logs parseable by monitoring tools. Consistent with modern observability. |
| D48 | Template engine | Jinja2 for platform captions | Clean separation of caption structure from data. Reusable across platforms. |
| D49 | EC2 timezone | America/New_York | Cron fires at wall-clock Eastern time. Automatically handles EST/EDT. |
| D50 | Log retention | 30 days local. Canonical trail in MySQL. | Log files are supplementary. video_runs + video_uploads are the source of truth. |
| D51 | Monthly cost | **AMENDED (R3, R5):** ~$25-57 incremental | ElevenLabs $22 + Claude ~$3-5 + S3/R2 ~$0.02 + possible EC2 upgrade ~$30. Pending R3 benchmark. |

## Review Amendments (from Section 9 Assessment)

### Amended Existing Decisions

| Decision | Change | Driver |
|----------|--------|--------|
| D4 | Add stale-content guard: `brief.date == run_date` assertion in EXTRACT | R6 |
| D6 | Add transient-media S3/R2 bucket for IG upload URLs; Drive remains archive | R5 |
| D10 | LLM model specified: `claude-sonnet-4-20250514` for script generation | R10 |
| D13 | LLM emits canonical numbers ($4.16); deterministic `format_for_speech()` produces TTS form | R2 |
| D33 | **REPLACED:** Presigned S3/R2 URL (15-min expiry) instead of temp-public Drive link | R5 |
| D40 | **ANNOTATED:** Briefs >90 days cannot be re-rendered. Accepted trade-off for DB hygiene. | R12 |
| D43 | Split health check: infra at 0600 ET, content at 0730 ET | R6 |
| D45 | Added --approve and --kill CLI flags for publish gate | R1 |
| D51 | Cost range updated to $25-57/mo pending R3 render benchmark | R3 |

### New Decisions

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| D52 | Publish gate | Phased rollout: preview (wk1-4) -> gate (wk5-8) -> auto (wk9+). PUBLISH_MODE env var. | Protect credibility brand. Kill switch without losing hands-off goal. (R1) |
| D53 | Number formatting | Two-step: LLM canonical -> Python `format_for_speech()` -> ElevenLabs | Eliminates numeric drift. Every number verifiable against source data. (R2) |
| D54 | UTM tagging | All CTA links UTM-tagged per platform and clip ID at launch | Attribute CIFaaS/Substack signups to specific videos. Zero infra cost. (R4) |
| D55 | Captions | SRT/VTT from existing word timestamps. Burned-in for IG. Platform tracks for YT/FB/LI. | Sound-off reach + accessibility. Near-zero cost from existing data. (R9) |
| D56 | Transient media bucket | S3 or Cloudflare R2 for IG presigned URLs | Drive can't serve raw bytes >25MB. Presigned URLs are direct, private, auto-expiring. (R5) |
| D57 | Proper-noun gate | Unknown nouns in HOOK/LEAD trigger requires_review flag, overrides auto-publish | Highest-impact mispronunciation prevention. Ties into R1 gate. (R8) |
| D58 | Stale-content guard | EXTRACT asserts brief.date == run_date; abort if stale | Prevents yesterday's news publishing as today's video. (R6) |
| D59 | Render benchmark | Pre-launch blocker: measure wall-clock + peak memory on target EC2 | Determines if t3.medium holds or needs upgrade. Blocks cost model finalization. (R3) |
