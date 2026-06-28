# Section 9: Design Review — Assessment & Triage

**Document:** Assessment of recommendations register from design-phase review
**Owner:** COGNOSCERE LLC
**Status:** Triaged and accepted (2026-06-10)
**Input:** 09-review-recommendations.md (R1-R12, OC-1)

## Triage Summary

| ID | Tier | Recommendation | Verdict | Phase |
|----|------|----------------|---------|-------|
| R1 | 1 | Human review gate | Accept with modification (phased rollout) | Pre-launch |
| R2 | 1 | Fact verification | Partial accept (D13 number formatting only) | Pre-launch |
| R3 | 1 | Benchmark render infra | Strong accept | Pre-launch blocker |
| R4 | 1 | Measurement loop | Accept, defer (UTM tags at launch, metrics table post-launch) | Early post-launch |
| R5 | 2 | IG presigned URL | Strong accept (design bug) | Pre-launch blocker |
| R6 | 2 | Event-driven trigger + stale guard | Partial accept (stale guard yes, event-driven defer) | Pre-launch |
| R7 | 2 | Platform limit validation | Accept (build-time checklist) | Early post-launch |
| R8 | 2 | TTS fallback + proper-noun gate | Partial accept (proper-noun gate yes, secondary TTS defer) | Early post-launch |
| R9 | 3 | SRT/VTT captions | Strong accept | Early post-launch |
| R10 | 3 | Name LLM model | Accept | Early post-launch |
| R11 | 3 | Secrets Manager | Defer to hardening phase | Hardening |
| R12 | 3 | Annotate operational realities | Accept | Early post-launch |

## Pre-Launch Blockers

These must be resolved before the first public run:

### 1. R3 — Benchmark Render Infrastructure
The $0 incremental infra claim is the least-supported in the design. Remotion drives headless Chromium; 8 renders at 1080p/30fps on a t3.medium (2 vCPU, 4GB) risks OOM and burst-credit exhaustion.

**Action:** Before implementation code, run a minimal Remotion benchmark on the EC2 instance. Measure wall-clock time and peak memory. Likely outcome: upgrade to t3.large (~$30/mo) or c6i.large. Update D3 and D51 with measured figures.

### 2. R5 — Fix Instagram Upload Mechanism (Design Bug)
Google Drive "anyone with link" does NOT serve raw video bytes for files >25MB. It returns an HTML interstitial page. The IG Graph API will receive HTML, not video, and reject the container.

**Action:** Add a small S3 or Cloudflare R2 bucket for transient upload URLs. Upload clip, generate presigned URL (15-min expiry), hand to IG API. Drive remains the archive. Cost: ~$0.02/month.

### 3. R6 (partial) — Stale-Content Guard
Without `brief.date == run_date`, a CDB pipeline failure means yesterday's news publishes as today's video.

**Action:** Add date assertion to EXTRACT stage. Split health check: infra at 0600 ET, content at 0730 ET (after CDB completion).

### 4. R1 (modified) — Phased Publish Mode
Pipeline starts in preview mode, graduates to auto-publish:
- **Weeks 1-4:** `PUBLISH_MODE=preview`. Script + preview emailed at 0700 ET. Manual approval triggers posting.
- **Weeks 5-8:** `PUBLISH_MODE=gate`. Auto-publishes at 0800 unless killed. Script emailed at 0700 for optional review.
- **Week 9+:** `PUBLISH_MODE=auto`. Fully automated. Kill switch remains available.

**Action:** Add `PUBLISH_MODE` env var. Add `--approve` CLI flag. Modify Stage 6 to check mode.

### 5. R2 (partial) — Deterministic Number Formatting
LLM must not emit spoken forms ("four-sixteen"). LLM emits canonical values ($4.16). A deterministic Python formatter produces the spoken form for TTS. Eliminates numeric drift.

**Action:** Add `format_for_speech()` utility. Amend D13. Modify Stage 2 LLM prompt to require canonical numbers.

## Early Post-Launch (Weeks 1-4)

### 6. R9 — SRT/VTT Caption Generation
Word-level timestamps already exist. ~20 lines of code to emit subtitle files. Platforms favor captioned uploads. Sound-off accessibility win.

**Action:** Add caption generation to Stage 5. Upload captions on YouTube (SRT via captions API) and Facebook. For Instagram, burn captions into the video render (no separate track support).

### 7. R4 (partial) — UTM Tagging
UTM-tag all CTA links in captions/descriptions immediately. This is a Jinja2 template change. Format: `?utm_source=youtube&utm_medium=video&utm_campaign=cdb-{date}&utm_content={clip_id}`

**Action:** Update caption templates in Section 5. Zero infrastructure.

### 8. R7 — Platform Limit Verification
Confirm at build time: Remotion outputs H.264/AAC (not VP9/WebM). Verify current IG Reels API duration limit. Document confirmed limits with "last verified" dates.

**Action:** Add "Platform Limits Verification" checklist to Section 8 Phase 7.

### 9. R8 (partial) — Proper-Noun Gate for HOOK/LEAD
If pronunciation dictionary scan finds an unknown proper noun in HOOK or LEAD, set a `requires_review` flag. In `gate` or `auto` publish mode, route to operator for approval before posting.

**Action:** Add proper-noun check after SSML injection in Stage 3. Add `requires_review` flag to spec/run.

### 10. R10 — Specify LLM Model
Script generation (Stage 2): `claude-sonnet-4-20250514`. Strong editorial judgment, fast, cost-effective. Opus is overkill for summarizing existing CIF records. Recomputed cost: ~$3-5/month.

**Action:** Add model spec to D10. Update Section 2.

### 11. R12 — Documentation Annotations
- D40: "Briefs older than 90 days cannot be re-rendered. Accepted trade-off."
- Section 5 token table: "Meta 60-day page token requires periodic manual re-auth. ~6/year."

## Hardening (As Cadence Stabilizes)

### 12. R4 (full) — video_metrics Table + METRICS Stage
Add delayed metrics pull (24-48h post-run) from each platform API. New `video_metrics` table. Closes the learning loop.

### 13. R11 — Secrets Manager Migration
Move credentials from .env to AWS Secrets Manager / SSM. Relevant when pursuing federal contracts (NIST 800-171).

### 14. R8 (full) — Secondary TTS Fallback
Only if ElevenLabs reliability becomes an observed problem. Adding a fallback TTS means maintaining two voice configurations and accepting inconsistent voice quality.

## Rejected / Not Accepted

### R2 (full verification stage) — DEFERRED
Full VERIFY stage with LLM claim-support pass is over-engineered for v1. The CDB pipeline already verifies claims. The script summarizes existing, source-attributed CIF records. Revisit if hallucination becomes observed.

### R6 (event-driven trigger) — DEFERRED
Event-driven CDB-completion sentinel adds cross-pipeline coupling. Simpler fix: split health check timing + stale-content guard. Cron trigger is sufficient for v1.

### R8 (secondary TTS) — DEFERRED
Maintaining two TTS providers (different voice quality) undermines "your voice" brand consistency. ElevenLabs uptime is high. One missed day < complexity of degraded fallback.

### R11 (Secrets Manager) — DEFERRED
Valid for federal posture, not launch-blocking. EC2 in VPC with SSH-only access. Standard for single-operator pipelines. Revisit for NIST compliance.

## Amended Architecture

Updated 8-stage pipeline incorporating accepted changes:

```
[Cron 0800 ET] -> Python Orchestrator
                    |
                    +-- Stage 1: EXTRACT  -- Read clusters + ASSERT brief.date == run_date
                    +-- Stage 2: SCRIPT   -- LLM generates script (canonical numbers, named model)
                    +-- Stage 2b: FORMAT  -- Deterministic number-to-speech formatting
                    +-- Stage 3: AUDIO    -- ElevenLabs + SSML + proper-noun gate check
                    +-- Stage 4: SPEC     -- Build Remotion input JSON
                    +-- Stage 5: RENDER   -- Remotion produces videos + captions (SRT/VTT)
                    +-- Stage 5b: GATE    -- If PUBLISH_MODE != auto, email preview + await approval
                    +-- Stage 6: POST     -- Upload to platforms (via presigned S3/R2 for IG)
                    +-- Stage 7: ARCHIVE  -- All artifacts to Google Drive
                    +-- Stage 8: LOG      -- Write run record to video_runs table
```
