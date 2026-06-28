# Section 6: Database Schema

## Design Principle

The NewsBrief pipeline reads from the existing `cdb` schema and writes to new tables in the same database. No new database needed.

## 6.1 Existing Tables (Read Only)

| Table | Used Fields | Purpose |
|-------|------------|---------|
| briefs | id, issue_number, date, version, published_at | Identify latest brief to process |
| clusters | id, brief_id, headline, body, why_this_matters, what_changed, status, confidence, position | Story content for script generation |
| cluster_sources | cluster_id, source_name, source_url | Provenance for source attribution |

## 6.2 New Tables

### video_runs

One row per pipeline execution. Mirrors the CDB pipeline's `runs` table pattern.

```sql
CREATE TABLE video_runs (
    id              VARCHAR(32)  PRIMARY KEY,
    brief_id        INT          NOT NULL,
    issue_number    VARCHAR(16)  NOT NULL,
    run_date        DATE         NOT NULL,
    started_at      DATETIME(3)  NOT NULL,
    completed_at    DATETIME(3)  NULL,
    status          ENUM('running','completed','failed','partial') NOT NULL DEFAULT 'running',

    -- Stage timings (seconds)
    stage_extract_s     DECIMAL(8,2)  NULL,
    stage_script_s      DECIMAL(8,2)  NULL,
    stage_audio_s       DECIMAL(8,2)  NULL,
    stage_spec_s        DECIMAL(8,2)  NULL,
    stage_render_s      DECIMAL(8,2)  NULL,
    stage_post_s        DECIMAL(8,2)  NULL,
    stage_archive_s     DECIMAL(8,2)  NULL,
    total_duration_s    DECIMAL(8,2)  NULL,

    -- Failure info
    failed_stage    VARCHAR(32)   NULL,
    error_message   TEXT          NULL,

    -- Script metadata
    stories_selected    JSON      NULL,
    word_count          INT       NULL,
    audio_duration_s    DECIMAL(8,2)  NULL,

    -- Artifact locations
    drive_folder_url    VARCHAR(512)  NULL,
    spec_path           VARCHAR(512)  NULL,

    -- Cost tracking
    elevenlabs_chars    INT       NULL,
    llm_input_tokens    INT       NULL,
    llm_output_tokens   INT       NULL,

    created_at      DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    INDEX idx_run_date (run_date),
    INDEX idx_brief_id (brief_id),
    FOREIGN KEY (brief_id) REFERENCES briefs(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### video_uploads

One row per platform upload attempt. Normalized from video_runs because each run produces 6 uploads with independent success/failure.

```sql
CREATE TABLE video_uploads (
    id              INT          AUTO_INCREMENT PRIMARY KEY,
    run_id          VARCHAR(32)  NOT NULL,
    platform        ENUM('youtube_video','youtube_short','facebook_video','facebook_reel','instagram_reel','linkedin_video') NOT NULL,
    status          ENUM('pending','uploading','completed','failed','skipped') NOT NULL DEFAULT 'pending',

    -- Platform-specific IDs
    platform_id     VARCHAR(256)  NULL,
    platform_url    VARCHAR(512)  NULL,

    -- Upload metadata
    file_name       VARCHAR(256)  NOT NULL,
    file_size_bytes BIGINT        NULL,
    aspect_ratio    ENUM('16x9','9x16') NOT NULL,
    content_type    ENUM('anchor','micro_clip','thumbnail') NOT NULL,
    clip_id         VARCHAR(8)    NULL,

    -- Timing
    started_at      DATETIME(3)  NULL,
    completed_at    DATETIME(3)  NULL,
    duration_s      DECIMAL(8,2) NULL,

    -- Failure info
    retry_count     INT          NOT NULL DEFAULT 0,
    error_message   TEXT         NULL,

    created_at      DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    INDEX idx_run_id (run_id),
    INDEX idx_platform (platform),
    INDEX idx_status (status),
    FOREIGN KEY (run_id) REFERENCES video_runs(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### video_scripts

Stores generated script for each run. Separated from video_runs to avoid bloating the audit table.

```sql
CREATE TABLE video_scripts (
    id              INT          AUTO_INCREMENT PRIMARY KEY,
    run_id          VARCHAR(32)  NOT NULL UNIQUE,
    brief_id        INT          NOT NULL,

    -- Script by slot
    hook_copy       TEXT         NOT NULL,
    lead_copy       TEXT         NOT NULL,
    scan_copy       TEXT         NOT NULL,
    why_copy        TEXT         NOT NULL,
    close_copy      TEXT         NOT NULL,

    -- LLM decisions
    lead_cluster_id     INT      NOT NULL,
    scan_cluster_ids    JSON     NOT NULL,
    selection_rationale TEXT     NULL,

    -- Platform captions
    platform_meta       JSON    NULL,

    -- Full Remotion spec
    remotion_spec       JSON    NULL,

    created_at      DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    INDEX idx_run_id (run_id),
    FOREIGN KEY (run_id) REFERENCES video_runs(id),
    FOREIGN KEY (brief_id) REFERENCES briefs(id),
    FOREIGN KEY (lead_cluster_id) REFERENCES clusters(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### pronunciation_log

Tracks new proper nouns and review status.

```sql
CREATE TABLE pronunciation_log (
    id              INT          AUTO_INCREMENT PRIMARY KEY,
    word            VARCHAR(128) NOT NULL,
    first_seen_date DATE         NOT NULL,
    first_seen_run  VARCHAR(32)  NOT NULL,
    cluster_id      INT          NULL,

    status          ENUM('pending_review','added_to_dict','ignored') NOT NULL DEFAULT 'pending_review',
    reviewed_at     DATETIME(3)  NULL,
    ssml_markup     TEXT         NULL,

    created_at      DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    UNIQUE INDEX idx_word (word),
    INDEX idx_status (status),
    FOREIGN KEY (first_seen_run) REFERENCES video_runs(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

## 6.3 Schema Migration

```sql
-- Migration: 006_create_video_tables.sql
CREATE TABLE video_runs (...);
CREATE TABLE video_uploads (...);
CREATE TABLE video_scripts (...);
CREATE TABLE pronunciation_log (...);

INSERT INTO schema_migrations (version, description, applied_at)
VALUES (6, 'Create video brief pipeline tables', NOW());
```

## 6.4 Data Flow

```
READ:  briefs + clusters + cluster_sources
         |
WRITE: video_runs       (created at start, updated per stage)
       video_scripts     (written at Stage 2, updated at Stage 4)
       video_uploads     (one row per platform at Stage 6)
       pronunciation_log (new words flagged at Stage 3)
```

## 6.5 Retention

- **video_runs:** Keep indefinitely. Small rows.
- **video_scripts:** Keep script text indefinitely. Null `remotion_spec` JSON after 90 days (large).
- **video_uploads:** Keep indefinitely. Small rows.
- **pronunciation_log:** Keep indefinitely. Grows slowly.
