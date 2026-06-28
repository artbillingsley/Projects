-- migrations/006_create_video_tables.sql
-- NewsBrief video pipeline tables
-- Run against the 'cdb' database on RDS

CREATE TABLE IF NOT EXISTS video_runs (
    id              VARCHAR(32)  PRIMARY KEY,
    brief_date      DATE         NOT NULL,
    issue_number    VARCHAR(16)  NOT NULL,
    run_date        DATE         NOT NULL,
    started_at      DATETIME(3)  NOT NULL,
    completed_at    DATETIME(3)  NULL,
    status          ENUM('running','completed','failed','partial') NOT NULL DEFAULT 'running',

    stage_extract_s     DECIMAL(8,2)  NULL,
    stage_script_s      DECIMAL(8,2)  NULL,
    stage_audio_s       DECIMAL(8,2)  NULL,
    stage_spec_s        DECIMAL(8,2)  NULL,
    stage_render_s      DECIMAL(8,2)  NULL,
    stage_post_s        DECIMAL(8,2)  NULL,
    stage_archive_s     DECIMAL(8,2)  NULL,
    total_duration_s    DECIMAL(8,2)  NULL,

    failed_stage    VARCHAR(32)   NULL,
    error_message   TEXT          NULL,

    stories_selected    JSON      NULL,
    word_count          INT       NULL,
    audio_duration_s    DECIMAL(8,2)  NULL,

    drive_folder_url    VARCHAR(512)  NULL,
    spec_path           VARCHAR(512)  NULL,

    elevenlabs_chars    INT       NULL,
    llm_input_tokens    INT       NULL,
    llm_output_tokens   INT       NULL,

    created_at      DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    INDEX idx_run_date (run_date),
    INDEX idx_brief_date (brief_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS video_uploads (
    id              INT          AUTO_INCREMENT PRIMARY KEY,
    run_id          VARCHAR(32)  NOT NULL,
    platform        VARCHAR(32)  NOT NULL,
    status          ENUM('pending','uploading','completed','failed','skipped') NOT NULL DEFAULT 'pending',

    platform_id     VARCHAR(256)  NULL,
    platform_url    VARCHAR(512)  NULL,

    file_name       VARCHAR(256)  NOT NULL,
    file_size_bytes BIGINT        NULL,
    aspect_ratio    VARCHAR(8)    NOT NULL,
    content_type    VARCHAR(16)   NOT NULL,
    clip_id         VARCHAR(8)    NULL,

    started_at      DATETIME(3)  NULL,
    completed_at    DATETIME(3)  NULL,
    duration_s      DECIMAL(8,2) NULL,

    retry_count     INT          NOT NULL DEFAULT 0,
    error_message   TEXT         NULL,

    created_at      DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    INDEX idx_run_id (run_id),
    INDEX idx_platform (platform),
    INDEX idx_status (status),
    FOREIGN KEY (run_id) REFERENCES video_runs(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS video_scripts (
    id              INT          AUTO_INCREMENT PRIMARY KEY,
    run_id          VARCHAR(32)  NOT NULL UNIQUE,
    brief_date      DATE         NOT NULL,

    hook_copy       TEXT         NOT NULL,
    lead_copy       TEXT         NOT NULL,
    scan_copy       TEXT         NOT NULL,
    why_copy        TEXT         NOT NULL,
    close_copy      TEXT         NOT NULL,

    lead_cluster_id     VARCHAR(36)  NOT NULL,
    scan_cluster_ids    JSON         NOT NULL,
    selection_rationale TEXT         NULL,

    platform_meta       JSON    NULL,
    remotion_spec       JSON    NULL,

    created_at      DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    INDEX idx_run_id (run_id),
    FOREIGN KEY (run_id) REFERENCES video_runs(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS pronunciation_log (
    id              INT          AUTO_INCREMENT PRIMARY KEY,
    word            VARCHAR(128) NOT NULL,
    first_seen_date DATE         NOT NULL,
    first_seen_run  VARCHAR(32)  NOT NULL,
    cluster_id      VARCHAR(36)  NULL,

    status          ENUM('pending_review','added_to_dict','ignored') NOT NULL DEFAULT 'pending_review',
    reviewed_at     DATETIME(3)  NULL,
    ssml_markup     TEXT         NULL,

    created_at      DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    UNIQUE INDEX idx_word (word),
    INDEX idx_status (status),
    FOREIGN KEY (first_seen_run) REFERENCES video_runs(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO schema_migrations (version, description, applied_at)
VALUES (6, 'Create video brief pipeline tables', NOW());
