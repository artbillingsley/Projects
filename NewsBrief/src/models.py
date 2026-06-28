# src/models.py
"""
SQLAlchemy 2.0 ORM models for the NewsBrief pipeline.

CDB tables (read-only):
    Brief, Cluster, ClusterSource

Video pipeline tables (read/write):
    VideoRun, VideoScript, VideoUpload, PronunciationLog
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, List, Optional

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# CDB read-only tables
# ---------------------------------------------------------------------------


class Brief(Base):
    """Existing CDB briefs table — read-only."""

    __tablename__ = "briefs"

    brief_date: Mapped[date] = mapped_column(Date, primary_key=True)
    methodology_version: Mapped[str] = mapped_column(String(64))
    issue_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    one_breath: Mapped[str] = mapped_column(Text)
    cluster_ids: Mapped[Any] = mapped_column(JSON)
    scan_layer: Mapped[Any] = mapped_column(JSON)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)


class Cluster(Base):
    """Existing CDB clusters table — read-only."""

    __tablename__ = "clusters"

    cluster_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    cif_code: Mapped[str] = mapped_column(String(8))
    first_seen: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(32))
    headline: Mapped[str] = mapped_column(String(512))
    summary: Mapped[str] = mapped_column(Text)  # this is the "body"
    what_changed: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    why_this_matters: Mapped[str] = mapped_column(Text)
    confidence: Mapped[str] = mapped_column(String(16))
    word_count: Mapped[int] = mapped_column(Integer)
    tier: Mapped[int] = mapped_column(Integer)

    sources: Mapped[List["ClusterSource"]] = relationship(
        back_populates="cluster",
        lazy="selectin",
        primaryjoin="Cluster.cluster_id == ClusterSource.cluster_id",
        foreign_keys="ClusterSource.cluster_id",
    )


class ClusterSource(Base):
    """Existing CDB cluster_sources table — read-only."""

    __tablename__ = "cluster_sources"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    cluster_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("clusters.cluster_id")
    )
    name: Mapped[str] = mapped_column(String(256))   # NOT source_name
    url: Mapped[str] = mapped_column(String(2048))   # NOT source_url

    # Relationships
    cluster: Mapped["Cluster"] = relationship(back_populates="sources")


# ---------------------------------------------------------------------------
# Video pipeline tables (new)
# ---------------------------------------------------------------------------


class VideoRun(Base):
    """One row per pipeline execution."""

    __tablename__ = "video_runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    brief_date: Mapped[date] = mapped_column(Date, nullable=False)
    issue_number: Mapped[str] = mapped_column(String(16), nullable=False)
    run_date: Mapped[date] = mapped_column(Date, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")

    # Stage timings (seconds)
    stage_extract_s: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 2), nullable=True
    )
    stage_script_s: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 2), nullable=True
    )
    stage_audio_s: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 2), nullable=True
    )
    stage_spec_s: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 2), nullable=True
    )
    stage_render_s: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 2), nullable=True
    )
    stage_post_s: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 2), nullable=True
    )
    stage_archive_s: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 2), nullable=True
    )
    total_duration_s: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 2), nullable=True
    )

    # Failure info
    failed_stage: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Script metadata
    stories_selected: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    word_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    audio_duration_s: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 2), nullable=True
    )

    # Artifact locations
    drive_folder_url: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True
    )
    spec_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Cost tracking
    elevenlabs_chars: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    llm_input_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    llm_output_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Relationships
    script: Mapped[Optional["VideoScript"]] = relationship(
        "VideoScript",
        back_populates="run",
        uselist=False,
        lazy="selectin",
    )
    uploads: Mapped[List["VideoUpload"]] = relationship(
        "VideoUpload",
        back_populates="run",
        lazy="selectin",
    )
    pronunciation_logs: Mapped[List["PronunciationLog"]] = relationship(
        "PronunciationLog",
        back_populates="first_seen_run_obj",
        lazy="selectin",
    )


class VideoScript(Base):
    """Generated script for one pipeline run."""

    __tablename__ = "video_scripts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("video_runs.id"), nullable=False, unique=True
    )
    brief_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Script slots
    hook_copy: Mapped[str] = mapped_column(Text, nullable=False)
    lead_copy: Mapped[str] = mapped_column(Text, nullable=False)
    scan_copy: Mapped[str] = mapped_column(Text, nullable=False)
    why_copy: Mapped[str] = mapped_column(Text, nullable=False)
    close_copy: Mapped[str] = mapped_column(Text, nullable=False)

    # LLM decisions
    lead_cluster_id: Mapped[str] = mapped_column(String(36), nullable=False)
    scan_cluster_ids: Mapped[list] = mapped_column(JSON, nullable=False)
    selection_rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Platform captions
    platform_meta: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Full Remotion spec
    remotion_spec: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Relationships
    run: Mapped["VideoRun"] = relationship("VideoRun", back_populates="script")


class VideoUpload(Base):
    """One row per platform upload attempt."""

    __tablename__ = "video_uploads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("video_runs.id"), nullable=False
    )
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")

    # Platform-specific IDs
    platform_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    platform_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Upload metadata
    file_name: Mapped[str] = mapped_column(String(256), nullable=False)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    aspect_ratio: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    content_type: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    clip_id: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)

    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_s: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2), nullable=True)

    # Failure info
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Relationships
    run: Mapped["VideoRun"] = relationship("VideoRun", back_populates="uploads")


class PronunciationLog(Base):
    """Tracks new proper nouns and review status."""

    __tablename__ = "pronunciation_log"

    __table_args__ = (UniqueConstraint("word", name="idx_word"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    word: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    first_seen_date: Mapped[date] = mapped_column(Date, nullable=False)
    first_seen_run: Mapped[str] = mapped_column(
        String(32), ForeignKey("video_runs.id"), nullable=False
    )
    cluster_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending_review"
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ssml_markup: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Relationships
    first_seen_run_obj: Mapped["VideoRun"] = relationship(
        "VideoRun",
        foreign_keys=[first_seen_run],
        back_populates="pronunciation_logs",
    )
