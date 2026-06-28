# src/run.py
"""
NewsBrief pipeline entry point.

Wires stages 1-2b together with CLI argument parsing.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import date, datetime
from typing import List, Optional


def parse_args(argv: List[str]) -> argparse.Namespace:
    """Parse command-line arguments for the NewsBrief pipeline."""
    parser = argparse.ArgumentParser(
        description="Run the NewsBrief video pipeline."
    )
    parser.add_argument(
        "--date",
        default=None,
        help="ISO date string (YYYY-MM-DD) to run against. Defaults to today.",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        default=False,
        help="Run in preview mode (no publish).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Print the formatted script and exit without proceeding to stages 3+.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Force re-run even if a run already exists for this date.",
    )
    parser.add_argument(
        "--stage",
        default=None,
        help="Run only up to this stage (e.g. 'extract', 'script', 'format').",
    )
    parser.add_argument(
        "--approve",
        action="store_true",
        default=False,
        help="Auto-approve the script review gate.",
    )
    parser.add_argument(
        "--kill",
        action="store_true",
        default=False,
        help="Abort any in-progress run for this date.",
    )
    parser.add_argument(
        "--platform",
        default=None,
        help="Target platform override (e.g. 'youtube', 'instagram').",
    )
    return parser.parse_args(argv)


def resolve_run_date(date_str: Optional[str]) -> date:
    """Return today's date if date_str is None, else parse ISO format."""
    if date_str is None:
        return date.today()
    return date.fromisoformat(date_str)


def main(argv: Optional[List[str]] = None) -> int:
    """
    Orchestrate pipeline stages 1-8 (full pipeline).

    Returns an exit code (0 = success, 1 = failure).
    """
    import structlog

    log = structlog.get_logger()

    if argv is None:
        argv = sys.argv[1:]

    args = parse_args(argv)
    run_date = resolve_run_date(args.date)

    log.info("pipeline.start", run_date=str(run_date), dry_run=args.dry_run)

    # -- Lazy imports for heavy dependencies (not needed during tests) --
    from src.config import load_config
    from src.lib.db import get_engine, get_session
    from src.models import VideoRun
    from src.stages.extract import extract
    from src.stages.format_speech import format_for_speech
    from src.stages.script import generate_script

    # In-memory tracking object (no DB write in dev — no live DB available)
    run_id = datetime.utcnow().strftime("run_%Y%m%d_%H%M%S")
    video_run = VideoRun(
        id=run_id,
        brief_date=run_date,  # updated after extract
        issue_number="",
        run_date=run_date,
        started_at=datetime.utcnow(),
        status="running",
    )

    wall_start = time.monotonic()

    try:
        # Load config
        config = load_config()

        # Create DB session
        engine = get_engine(config)
        session = get_session(engine)

        # ----------------------------------------------------------------
        # Stage 1: Extract
        # ----------------------------------------------------------------
        stage1_start = time.monotonic()
        extract_result = extract(session, run_date)
        video_run.brief_date = extract_result.brief_date
        video_run.issue_number = extract_result.issue_number
        video_run.stage_extract_s = round(time.monotonic() - stage1_start, 2)

        log.info(
            "stage1.extract.complete",
            brief_id=extract_result.brief_id,
            issue=extract_result.issue_number,
            clusters=len(extract_result.clusters),
            duration_s=video_run.stage_extract_s,
        )

        # ----------------------------------------------------------------
        # Stage 2: Script generation (Anthropic)
        # ----------------------------------------------------------------
        import anthropic  # heavy import — only when actually running

        client = anthropic.Anthropic(api_key=config.anthropic_api_key)

        stage2_start = time.monotonic()
        script_result = generate_script(extract_result, client)
        video_run.stage_script_s = round(time.monotonic() - stage2_start, 2)
        video_run.llm_input_tokens = script_result.input_tokens
        video_run.llm_output_tokens = script_result.output_tokens
        video_run.word_count = script_result.word_count

        log.info(
            "stage2.script.complete",
            lead_cluster_id=script_result.lead_cluster_id,
            word_count=script_result.word_count,
            input_tokens=script_result.input_tokens,
            output_tokens=script_result.output_tokens,
            duration_s=video_run.stage_script_s,
        )

        # ----------------------------------------------------------------
        # Stage 2b: Format for speech (number-to-words)
        # ----------------------------------------------------------------
        formatted = {
            "hook": format_for_speech(script_result.hook),
            "lead": format_for_speech(script_result.lead),
            "scan_intro": format_for_speech(script_result.scan_intro),
            "scan_items": [format_for_speech(item) for item in script_result.scan_items],
            "why": format_for_speech(script_result.why),
            "close": format_for_speech(script_result.close),
        }

        log.info("stage2b.format.complete", slots=list(formatted.keys()))

        # ----------------------------------------------------------------
        # --dry-run: print script and exit
        # ----------------------------------------------------------------
        if args.dry_run:
            print("\n=== DRY RUN — Formatted Script ===\n")
            print(f"[HOOK]  {formatted['hook']}\n")
            print(f"[LEAD]  {formatted['lead']}\n")
            print(f"[SCAN]  {formatted['scan_intro']}")
            for i, item in enumerate(formatted["scan_items"], 1):
                print(f"        {i}. {item}")
            print(f"\n[WHY]   {formatted['why']}\n")
            print(f"[CLOSE] {formatted['close']}\n")
            video_run.status = "dry_run"
            return 0

        # ----------------------------------------------------------------
        # Stage 3: Audio generation (ElevenLabs)
        # ----------------------------------------------------------------
        from src.lib.pronunciation import load_dictionary
        from src.stages.audio import generate_all_audio

        stage3_start = time.monotonic()

        # Load pronunciation dictionary
        config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config")
        pronunciation = load_dictionary(os.path.join(config_dir, "pronunciation.yaml"))

        # Import ElevenLabs client
        import elevenlabs as el_sdk
        el_client = el_sdk.ElevenLabs(api_key=config.elevenlabs_api_key)

        # Generate audio for all slots
        audio_dir = os.path.abspath(os.path.join("tmp", run_date.isoformat(), "audio"))
        audio_result = generate_all_audio(
            script=script_result,
            el_client=el_client,
            voice_id=config.elevenlabs_voice_id,
            pronunciation=pronunciation,
            output_dir=audio_dir,
        )
        video_run.stage_audio_s = round(time.monotonic() - stage3_start, 2)
        video_run.audio_duration_s = audio_result.total_duration_seconds
        video_run.elevenlabs_chars = audio_result.total_characters

        log.info(
            "stage3.audio.complete",
            total_duration_s=audio_result.total_duration_seconds,
            total_chars=audio_result.total_characters,
            requires_review=audio_result.gate_result.requires_review,
            duration_s=video_run.stage_audio_s,
        )

        # Duration guardrail — target is 90 sec, YouTube Shorts cap is 3 min
        if audio_result.total_duration_seconds > 100:
            log.warning(
                "audio.duration_warning",
                duration_s=audio_result.total_duration_seconds,
                message="Video exceeds 100s target (aim for 90s)",
            )

        # ----------------------------------------------------------------
        # Stage 4: Build Remotion spec
        # ----------------------------------------------------------------
        from src.stages.spec import build_spec, save_spec

        stage4_start = time.monotonic()
        spec = build_spec(
            extract_result=extract_result,
            script_result=script_result,
            audio_result=audio_result,
            audio_dir=audio_dir,
        )

        spec_path = os.path.join("tmp", run_date.isoformat(), "remotion-spec.json")
        save_spec(spec, spec_path)
        video_run.stage_spec_s = round(time.monotonic() - stage4_start, 2)
        video_run.spec_path = spec_path

        log.info(
            "stage4.spec.complete",
            spec_path=spec_path,
            render_targets=len(spec.get("render_targets", [])),
            duration_s=video_run.stage_spec_s,
        )

        # ----------------------------------------------------------------
        # Stage 5: Render (Remotion via subprocess)
        # ----------------------------------------------------------------
        from src.stages.render import render_videos

        stage5_start = time.monotonic()
        output_dir = os.path.join("tmp", run_date.isoformat())
        renderer_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "newsbrief-renderer")

        render_videos(
            spec_path=os.path.abspath(spec_path),
            output_dir=os.path.abspath(output_dir),
            renderer_dir=os.path.abspath(renderer_dir),
            audio_dir=audio_dir,
        )
        video_run.stage_render_s = round(time.monotonic() - stage5_start, 2)

        log.info("stage5.render.complete", duration_s=video_run.stage_render_s)

        # ----------------------------------------------------------------
        # Stage 5b: Gate (publish mode check)
        # ----------------------------------------------------------------
        from src.stages.gate import check_gate

        gate_decision = check_gate(
            publish_mode=config.publish_mode,
            requires_review=audio_result.gate_result.requires_review,
            approved=args.approve,
            killed=args.kill,
        )

        log.info("stage5b.gate.decision", decision=gate_decision.value, should_publish=gate_decision.should_publish)

        if not gate_decision.should_publish:
            log.info("pipeline.gated", decision=gate_decision.value)
            # Send review email if in preview/gate mode
            try:
                from src.lib.alert import send_alert
                if config.alert_email_to:
                    send_alert(
                        template_name="gate_review.j2",
                        subject=f"[NewsBrief] Review Required - {run_date}",
                        to_email=config.alert_email_to,
                        from_email=config.alert_email_from,
                        date=str(run_date),
                        issue_number=extract_result.issue_number,
                        publish_mode=config.publish_mode,
                        requires_review=audio_result.gate_result.requires_review,
                        unknown_words=audio_result.gate_result.unknown_words,
                        hook=formatted["hook"],
                        lead=formatted["lead"],
                        scan=formatted["scan_intro"] + "\n" + "\n".join(formatted["scan_items"]),
                        why=formatted["why"],
                        close=formatted["close"],
                        word_count=script_result.word_count,
                    )
            except Exception as alert_err:
                log.error("gate.alert.failed", error=str(alert_err))
            video_run.status = "gated"
            return 0

        # ----------------------------------------------------------------
        # Stage 6: Post (platform uploads)
        # ----------------------------------------------------------------
        from src.stages.post import upload_all

        stage6_start = time.monotonic()
        upload_results = upload_all(
            output_dir=os.path.abspath(output_dir),
            spec=spec,
            config=config,
        )
        video_run.stage_post_s = round(time.monotonic() - stage6_start, 2)

        succeeded = [r for r in upload_results if r.status == "completed"]
        failed = [r for r in upload_results if r.status == "failed"]
        log.info(
            "stage6.post.complete",
            succeeded=len(succeeded),
            failed=len(failed),
            duration_s=video_run.stage_post_s,
        )

        # ----------------------------------------------------------------
        # Stage 7: Archive (Google Drive — video + caption markdown)
        # ----------------------------------------------------------------
        drive_url = None
        try:
            from src.stages.archive import archive_to_drive

            stage7_start = time.monotonic()
            # Get YouTube Short URL from upload results for caption cross-links
            yt_short_url = ""
            for r in upload_results:
                if r.platform == "youtube_short" and r.status == "completed" and r.platform_url:
                    yt_short_url = r.platform_url
                    break

            video_path = os.path.join(os.path.abspath(output_dir), "anchor-9x16.mp4")
            archive_result = archive_to_drive(
                config=config,
                spec=spec,
                video_path=video_path,
                date_str=run_date.isoformat(),
                youtube_url=yt_short_url,
            )
            if archive_result:
                drive_url = archive_result["video_link"]
            video_run.stage_archive_s = round(time.monotonic() - stage7_start, 2)
            video_run.drive_folder_url = drive_url
            log.info("stage7.archive.complete", drive_url=drive_url)
        except Exception as archive_err:
            log.error("stage7.archive.failed", error=str(archive_err))
            # Archive failure is non-blocking

        # ----------------------------------------------------------------
        # Stage 8: Log (save to DB + send alert)
        # ----------------------------------------------------------------
        try:
            from src.stages.log import save_run, save_uploads, save_script

            video_run.status = "completed" if not failed else "partial"
            video_run.stories_selected = [script_result.lead_cluster_id] + script_result.scan_cluster_ids
            save_run(session, video_run)
            save_uploads(session, run_id, upload_results)
            save_script(session, run_id, extract_result.brief_date, script_result, spec)
            log.info("stage8.log.complete")
        except Exception as log_err:
            log.error("stage8.log.failed", error=str(log_err))

        # Send success/failure alert
        try:
            from src.lib.alert import send_alert
            if config.alert_email_to:
                upload_count = len(succeeded)
                total_platforms = len(upload_results)
                send_alert(
                    template_name="alert_success.j2",
                    subject=f"[NewsBrief] {run_date} - {upload_count}/{total_platforms} platforms posted",
                    to_email=config.alert_email_to,
                    from_email=config.alert_email_from,
                    sendgrid_api_key=config.sendgrid_api_key,
                    brief_type="NewsBrief",
                    date=str(run_date),
                    issue_number=extract_result.issue_number,
                    duration=f"{video_run.total_duration_s}s",
                    upload_count=upload_count,
                    total_platforms=total_platforms,
                    uploads=[
                        {"platform": r.platform, "status": r.status, "url": r.platform_url or r.error_message or ""}
                        for r in upload_results
                    ],
                    elevenlabs_chars=video_run.elevenlabs_chars or 0,
                    elevenlabs_cost=round((video_run.elevenlabs_chars or 0) * 0.00003, 2),
                    llm_input_tokens=video_run.llm_input_tokens or 0,
                    llm_output_tokens=video_run.llm_output_tokens or 0,
                    llm_cost=round(((video_run.llm_input_tokens or 0) * 0.000003 + (video_run.llm_output_tokens or 0) * 0.000015), 2),
                    drive_url=drive_url,
                    pronunciation_new=len(audio_result.gate_result.unknown_words),
                )
        except Exception as alert_err:
            log.error("alert.failed", error=str(alert_err))

        video_run.status = "completed" if not failed else "partial"
        return 0

    except Exception as exc:
        video_run.status = "failed"
        video_run.failed_stage = "unknown"
        video_run.error_message = str(exc)
        log.error("pipeline.failed", error=str(exc))
        # Try to save failed run to DB
        try:
            from src.stages.log import save_run
            save_run(session, video_run)
        except Exception:
            pass  # DB may not be available
        # Send failure alert
        try:
            from src.lib.alert import send_alert
            if config.alert_email_to:
                send_alert(
                    template_name="alert_failure.j2",
                    subject=f"[NewsBrief] FAILED - {run_date}",
                    to_email=config.alert_email_to,
                    from_email=config.alert_email_from,
                    sendgrid_api_key=config.sendgrid_api_key,
                    brief_type="NewsBrief",
                    date=str(run_date),
                    issue_number=getattr(extract_result, "issue_number", "N/A") if "extract_result" in dir() else "N/A",
                    failed_stage=video_run.failed_stage,
                    duration=f"{round(time.monotonic() - wall_start, 2)}s",
                    error_message=str(exc),
                )
        except Exception:
            pass
        return 1

    finally:
        video_run.completed_at = datetime.utcnow()
        video_run.total_duration_s = round(time.monotonic() - wall_start, 2)
        log.info(
            "pipeline.finished",
            status=video_run.status,
            total_duration_s=video_run.total_duration_s,
        )


if __name__ == "__main__":
    sys.exit(main())
