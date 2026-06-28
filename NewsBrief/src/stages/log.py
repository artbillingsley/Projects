# src/stages/log.py
from __future__ import annotations

from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy.orm import Session

from src.models import VideoRun, VideoUpload, VideoScript

log = structlog.get_logger()


def save_run(session: Session, run: VideoRun) -> None:
    log.info("log.save_run", run_id=run.id, status=run.status)
    session.merge(run)
    session.commit()


def save_uploads(
    session: Session,
    run_id: str,
    upload_results: List[Any],
) -> None:
    for r in upload_results:
        upload = VideoUpload(
            run_id=run_id,
            platform=r.platform,
            status=r.status,
            platform_id=r.platform_id or None,
            platform_url=r.platform_url or None,
            file_name=r.file_name,
            aspect_ratio=r.aspect_ratio,
            content_type=r.content_type,
            clip_id=r.clip_id if hasattr(r, 'clip_id') else None,
            error_message=r.error_message or None,
        )
        session.add(upload)

    session.commit()
    log.info("log.uploads.saved", count=len(upload_results))


def save_script(
    session: Session,
    run_id: str,
    brief_date: Any,
    script_result: Any,
    spec: Optional[Dict] = None,
) -> None:
    vs = VideoScript(
        run_id=run_id,
        brief_date=brief_date,
        hook_copy=script_result.hook,
        lead_copy=script_result.lead,
        scan_copy=script_result.full_scan,
        why_copy=script_result.why,
        close_copy=script_result.close,
        lead_cluster_id=script_result.lead_cluster_id,
        scan_cluster_ids=script_result.scan_cluster_ids,
        selection_rationale=script_result.selection_rationale,
        platform_meta=script_result.platform_meta,
        remotion_spec=spec,
    )
    session.add(vs)
    session.commit()
    log.info("log.script.saved", run_id=run_id)
