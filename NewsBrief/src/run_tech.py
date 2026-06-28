# src/run_tech.py
"""
TechBrief pipeline entry point.

Produces a 90-second COGNOSCERE Tech Brief from DRS articles.
Reuses the NewsBrief audio, render, post, and archive infrastructure.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import date, datetime
from typing import List, Optional

import structlog

log = structlog.get_logger()


def main(argv: Optional[List[str]] = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(description="Run the TechBrief video pipeline.")
    parser.add_argument("--date", default=None)
    parser.add_argument("--dry-run", action="store_true", default=False)
    parser.add_argument("--approve", action="store_true", default=False)
    args = parser.parse_args(argv)

    run_date = date.fromisoformat(args.date) if args.date else date.today()
    log.info("techbrief.start", run_date=str(run_date))

    wall_start = time.monotonic()

    try:
        from src.config import load_config
        config = load_config()

        # ----------------------------------------------------------------
        # Stage 1: Extract from DRS
        # ----------------------------------------------------------------
        from src.stages.extract_tech import extract_tech

        stage1_start = time.monotonic()
        extract_result = extract_tech(run_date)

        if not extract_result.articles:
            log.error("techbrief.no_articles")
            return 1

        log.info("stage1.extract_tech.complete",
                 articles=len(extract_result.articles),
                 act=extract_result.act_count,
                 issue=extract_result.issue_number,
                 duration_s=round(time.monotonic() - stage1_start, 2))

        # ----------------------------------------------------------------
        # Stage 2: Script generation (Opus)
        # ----------------------------------------------------------------
        import anthropic
        from src.stages.script_tech import generate_tech_script

        client = anthropic.Anthropic(api_key=config.anthropic_api_key)

        stage2_start = time.monotonic()
        script = generate_tech_script(extract_result, client)

        log.info("stage2.script_tech.complete",
                 word_count=script.word_count,
                 duration_s=round(time.monotonic() - stage2_start, 2))

        # ----------------------------------------------------------------
        # Stage 2b: Format for speech
        # ----------------------------------------------------------------
        from src.stages.format_speech import format_for_speech

        formatted = {
            "hook": format_for_speech(script.hook),
            "lead": format_for_speech(script.lead),
            "scan_intro": format_for_speech(script.scan_intro),
            "scan_items": [format_for_speech(item) for item in script.scan_items],
            "why": format_for_speech(script.why),
            "close": format_for_speech(script.close),
        }

        if args.dry_run:
            print("\n=== DRY RUN — TechBrief Script ===\n")
            print(f"[HOOK]  {formatted['hook']}\n")
            print(f"[LEAD]  {formatted['lead']}\n")
            print(f"[SCAN]  {formatted['scan_intro']}")
            for i, item in enumerate(formatted["scan_items"], 1):
                print(f"        {i}. {item}")
            print(f"\n[WHY]   {formatted['why']}\n")
            print(f"[CLOSE] {formatted['close']}\n")
            print(f"\nWord count: {script.word_count}")
            return 0

        # ----------------------------------------------------------------
        # Stage 3: Audio (ElevenLabs)
        # ----------------------------------------------------------------
        from src.lib.pronunciation import load_dictionary
        from src.stages.audio import generate_all_audio

        stage3_start = time.monotonic()
        config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config")
        pronunciation = load_dictionary(os.path.join(config_dir, "pronunciation.yaml"))

        import elevenlabs as el_sdk
        el_client = el_sdk.ElevenLabs(api_key=config.elevenlabs_api_key)

        audio_dir = os.path.abspath(os.path.join("tmp", f"tech-{run_date.isoformat()}", "audio"))

        # Build a compatible ScriptResult-like object for generate_all_audio
        from src.stages.script import ScriptResult
        compat_script = ScriptResult(
            lead_cluster_id="",
            scan_cluster_ids=[],
            selection_rationale="",
            hook=script.hook,
            lead=script.lead,
            scan_intro=script.scan_intro,
            scan_items=script.scan_items,
            why=script.why,
            close=script.close,
            platform_meta=script.platform_meta,
            input_tokens=script.input_tokens,
            output_tokens=script.output_tokens,
            image_queries=script.image_queries,
        )

        audio_result = generate_all_audio(
            script=compat_script,
            el_client=el_client,
            voice_id=config.elevenlabs_voice_id,
            pronunciation=pronunciation,
            output_dir=audio_dir,
        )

        log.info("stage3.audio.complete",
                 duration_s=round(time.monotonic() - stage3_start, 2),
                 total_duration_s=audio_result.total_duration_seconds)

        if audio_result.total_duration_seconds > 100:
            log.warning("audio.duration_warning", duration_s=audio_result.total_duration_seconds)

        # ----------------------------------------------------------------
        # Stage 4: Build Remotion spec + fetch images
        # ----------------------------------------------------------------
        from src.stages.spec import save_spec, _scrape_og_image, _download_image

        stage4_start = time.monotonic()
        output_dir = os.path.join("tmp", f"tech-{run_date.isoformat()}")
        images_dir = os.path.join(os.path.abspath(output_dir), "images")
        os.makedirs(images_dir, exist_ok=True)

        # Fetch og:image for lead and each scan item from source URLs
        image_files = {}
        # Lead image
        lead_article = next((a for a in extract_result.articles if a.title == script.lead_title), None)
        if lead_article and lead_article.source_url:
            og = _scrape_og_image(lead_article.source_url)
            if og:
                path = _download_image(og, "lead", images_dir)
                if path:
                    image_files["lead"] = path
                    log.info("techbrief.image.lead", source=lead_article.source_name)

        # Scan item images
        for i, scan_title in enumerate(script.scan_titles):
            article = next((a for a in extract_result.articles if a.title == scan_title), None)
            if article and article.source_url:
                og = _scrape_og_image(article.source_url)
                if og:
                    path = _download_image(og, f"scan-{i}", images_dir)
                    if path:
                        image_files[f"scan-{i}"] = path
                        log.info("techbrief.image.scan", index=i, source=article.source_name)

        # Build a tech-specific spec
        spec = _build_tech_spec(extract_result, script, audio_result, audio_dir, run_date, image_files)

        spec_path = os.path.join(output_dir, "remotion-spec.json")
        save_spec(spec, spec_path)

        log.info("stage4.spec.complete", spec_path=spec_path,
                 duration_s=round(time.monotonic() - stage4_start, 2))

        # ----------------------------------------------------------------
        # Stage 5: Render
        # ----------------------------------------------------------------
        from src.stages.render import render_videos

        stage5_start = time.monotonic()
        renderer_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "newsbrief-renderer")

        render_videos(
            spec_path=os.path.abspath(spec_path),
            output_dir=os.path.abspath(output_dir),
            renderer_dir=os.path.abspath(renderer_dir),
            audio_dir=audio_dir,
        )

        log.info("stage5.render.complete", duration_s=round(time.monotonic() - stage5_start, 2))

        # ----------------------------------------------------------------
        # Stage 6: Post (same platforms as NewsBrief)
        # ----------------------------------------------------------------
        if not args.approve:
            log.info("techbrief.gated", reason="--approve not set")
            return 0

        from src.stages.post import upload_all

        stage6_start = time.monotonic()
        upload_results = upload_all(
            output_dir=os.path.abspath(output_dir),
            spec=spec,
            config=config,
        )

        succeeded = [r for r in upload_results if r.status == "completed"]
        failed = [r for r in upload_results if r.status == "failed"]
        log.info("stage6.post.complete", succeeded=len(succeeded), failed=len(failed))

        # ----------------------------------------------------------------
        # Stage 7: Archive to Google Drive
        # ----------------------------------------------------------------
        try:
            from src.stages.archive import archive_to_drive

            yt_short_url = ""
            for r in upload_results:
                if r.platform == "youtube_short" and r.status == "completed":
                    yt_short_url = r.platform_url
                    break

            video_path = os.path.join(os.path.abspath(output_dir), "anchor-9x16.mp4")
            archive_to_drive(
                config=config,
                spec=spec,
                video_path=video_path,
                date_str=f"tech-{run_date.isoformat()}",
                youtube_url=yt_short_url,
            )
            log.info("stage7.archive.complete")
        except Exception as e:
            log.error("stage7.archive.failed", error=str(e))

        # ----------------------------------------------------------------
        # Stage 8: Send alert
        # ----------------------------------------------------------------
        try:
            from src.lib.alert import send_alert
            if config.alert_email_to:
                upload_count = len(succeeded)
                total_platforms = len(upload_results)
                drive_url = ""
                send_alert(
                    template_name="alert_success.j2",
                    subject=f"[TechBrief] {run_date} - {upload_count}/{total_platforms} platforms posted",
                    to_email=config.alert_email_to,
                    from_email=config.alert_email_from,
                    sendgrid_api_key=config.sendgrid_api_key,
                    brief_type="TechBrief",
                    date=str(run_date),
                    issue_number=extract_result.issue_number,
                    duration=f"{round(time.monotonic() - wall_start, 2)}s",
                    upload_count=upload_count,
                    total_platforms=total_platforms,
                    uploads=[
                        {"platform": r.platform, "status": r.status, "url": r.platform_url or r.error_message or ""}
                        for r in upload_results
                    ],
                    elevenlabs_chars=audio_result.total_characters,
                    elevenlabs_cost=round(audio_result.total_characters * 0.00003, 2),
                    llm_input_tokens=script.input_tokens,
                    llm_output_tokens=script.output_tokens,
                    llm_cost=round((script.input_tokens * 0.000003 + script.output_tokens * 0.000015), 2),
                    drive_url=drive_url,
                )
        except Exception as alert_err:
            log.error("alert.failed", error=str(alert_err))

        log.info("techbrief.finished", status="completed",
                 total_duration_s=round(time.monotonic() - wall_start, 2))
        return 0

    except Exception as exc:
        log.error("techbrief.failed", error=str(exc))
        # Send failure alert
        try:
            from src.lib.alert import send_alert
            if config.alert_email_to:
                send_alert(
                    template_name="alert_failure.j2",
                    subject=f"[TechBrief] FAILED - {run_date}",
                    to_email=config.alert_email_to,
                    from_email=config.alert_email_from,
                    sendgrid_api_key=config.sendgrid_api_key,
                    brief_type="TechBrief",
                    date=str(run_date),
                    issue_number=extract_result.issue_number if "extract_result" in dir() else "N/A",
                    failed_stage="unknown",
                    duration=f"{round(time.monotonic() - wall_start, 2)}s",
                    error_message=str(exc),
                )
        except Exception:
            pass
        return 1


def _build_tech_spec(extract, script, audio_result, audio_dir, run_date, image_files=None):
    """Build a Remotion-compatible spec from TechBrief data."""
    if image_files is None:
        image_files = {}

    # Index audio slots by name for easy lookup (case-insensitive)
    audio_by_name = {s.slot_name.upper(): s for s in audio_result.slots}

    def get_words(slot_name):
        s = audio_by_name.get(slot_name.upper())
        return s.word_timings if s else []

    def get_duration(slot_name, default=5.0):
        s = audio_by_name.get(slot_name.upper())
        return s.duration_seconds if s else default

    # Build slots matching the NewsBrief spec format
    slots = []

    # Determine sources for the lead
    lead_sources = [script.lead_source] if script.lead_source else []
    for s in script.scan_sources:
        if s not in lead_sources:
            lead_sources.append(s)

    # HOOK slot (uses lead image)
    slots.append({
        "type": "HOOK",
        "copy": script.hook,
        "audio_file": "audio/hook.mp3",
        "words": get_words("hook"),
        "duration_seconds": get_duration("hook", 5),
        "image_file": image_files.get("lead"),
        "gfx": {"headline": script.lead_title, "sources": lead_sources},
    })

    # LEAD slot
    slots.append({
        "type": "LEAD",
        "copy": script.lead,
        "audio_file": "audio/lead.mp3",
        "words": get_words("lead"),
        "duration_seconds": get_duration("lead", 25),
        "image_file": image_files.get("lead"),
        "gfx": {
            "headline": script.lead_title,
            "sources": lead_sources,
            "cif_tag": extract.issue_number,
            "status": "ACT" if extract.act_count > 0 else "PREPARE",
        },
    })

    # SCAN slot
    scan_items = []
    for i, (item_text, title, source) in enumerate(
        zip(script.scan_items, script.scan_titles, script.scan_sources)
    ):
        scan_items.append({
            "copy": item_text,
            "headline": title,
            "cif_tag": extract.issue_number,
            "status": "PREPARE",
            "image_file": image_files.get(f"scan-{i}"),
        })

    slots.append({
        "type": "SCAN",
        "copy": script.scan_intro,
        "intro_copy": script.scan_intro,
        "audio_file": "audio/scan.mp3",
        "words": get_words("scan"),
        "duration_seconds": get_duration("scan", 40),
        "items": scan_items,
    })

    # WHY slot (uses lead image)
    slots.append({
        "type": "WHY",
        "copy": script.why,
        "audio_file": "audio/why.mp3",
        "words": get_words("why"),
        "duration_seconds": get_duration("why", 10),
        "image_file": image_files.get("lead"),
    })

    # CLOSE slot
    slots.append({
        "type": "CLOSE",
        "copy": script.close,
        "audio_file": "audio/close.mp3",
        "words": get_words("close"),
        "duration_seconds": get_duration("close", 5),
    })

    spec = {
        "date": run_date.isoformat(),
        "issue_number": extract.issue_number,
        "brief_id": f"tech-{run_date.isoformat()}",
        "slots": slots,
        "clips": [],
        "render_targets": [],
        "requires_review": False,
        "unknown_words": [],
        "total_duration_seconds": audio_result.total_duration_seconds,
        "source_names": lead_sources,
    }

    return spec


if __name__ == "__main__":
    sys.exit(main())
