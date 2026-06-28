# src/healthcheck.py
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from datetime import date
from typing import Callable, List, Tuple

import requests
import structlog

log = structlog.get_logger()


def check_mysql_connection(config) -> bool:
    from src.lib.db import get_engine
    try:
        engine = get_engine(config)
        with engine.connect() as conn:
            conn.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
        return True
    except Exception as e:
        log.error("healthcheck.mysql.failed", error=str(e))
        return False


def check_anthropic_ping(config) -> bool:
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=config.anthropic_api_key)
        client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=5,
            messages=[{"role": "user", "content": "ping"}],
        )
        return True
    except Exception as e:
        log.error("healthcheck.anthropic.failed", error=str(e))
        return False


def check_elevenlabs_ping(config) -> bool:
    if not config.elevenlabs_api_key:
        log.warning("healthcheck.elevenlabs.skipped", reason="no API key")
        return True
    try:
        import elevenlabs
        client = elevenlabs.ElevenLabs(api_key=config.elevenlabs_api_key)
        client.voices.get_all()
        return True
    except Exception as e:
        log.error("healthcheck.elevenlabs.failed", error=str(e))
        return False


def check_disk_space() -> bool:
    usage = shutil.disk_usage("/")
    free_gb = usage.free / (1024 ** 3)
    if free_gb < 2.0:
        log.error("healthcheck.disk.low", free_gb=round(free_gb, 1))
        return False
    return True


def check_node_installed() -> bool:
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except Exception:
        return False


def check_ffmpeg_installed() -> bool:
    """Check for FFmpeg — try system PATH first, then Remotion's bundled copy."""
    import os
    paths = [
        "ffmpeg",
        os.path.expanduser("~/newsbrief/newsbrief-renderer/node_modules/@remotion/compositor-linux-x64-gnu/ffmpeg"),
    ]
    for path in paths:
        try:
            result = subprocess.run([path, "-version"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return True
        except Exception:
            continue
    return False


def check_brief_exists(config, run_date: date) -> bool:
    from src.lib.db import get_engine, get_session
    from src.models import Brief
    engine = get_engine(config)
    session = get_session(engine)
    try:
        brief = session.query(Brief).filter(Brief.date == run_date).first()
        if brief is None:
            log.warning("healthcheck.brief.not_found", date=str(run_date))
            return False
        return True
    finally:
        session.close()


def check_meta_token(access_token: str) -> bool:
    """Validate a Meta access token via the debug_token endpoint."""
    if not access_token:
        log.warning("healthcheck.meta.skipped", reason="no token")
        return True
    try:
        resp = requests.get(
            "https://graph.facebook.com/debug_token",
            params={"input_token": access_token, "access_token": access_token},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})
        is_valid = data.get("is_valid", False)
        if not is_valid:
            error_msg = data.get("error", {}).get("message", "unknown")
            log.error("healthcheck.meta.invalid", error=error_msg)
        return is_valid
    except Exception as e:
        log.error("healthcheck.meta.failed", error=str(e))
        return False


def main():
    parser = argparse.ArgumentParser(description="NewsBrief Health Check")
    parser.add_argument("--infra", action="store_true", help="Run infrastructure checks only")
    parser.add_argument("--content", action="store_true", help="Run content checks only")
    args = parser.parse_args()

    from src.config import load_config
    config = load_config()
    today = date.today()

    results: List[Tuple[str, bool]] = []

    if args.infra or (not args.infra and not args.content):
        infra_checks: List[Tuple[str, Callable]] = [
            ("MySQL connection", lambda: check_mysql_connection(config)),
            ("Claude API", lambda: check_anthropic_ping(config)),
            ("ElevenLabs API", lambda: check_elevenlabs_ping(config)),
            ("Disk space >2GB", check_disk_space),
            ("Node.js installed", check_node_installed),
            ("FFmpeg installed", check_ffmpeg_installed),
            ("Meta token (FB/IG)", lambda: check_meta_token(config.facebook_access_token)),
        ]
        for name, fn in infra_checks:
            ok = fn()
            status = "OK" if ok else "FAIL"
            results.append((name, ok))
            print(f"  [{status}] {name}")

    if args.content or (not args.infra and not args.content):
        content_checks: List[Tuple[str, Callable]] = [
            ("Today's brief exists", lambda: check_brief_exists(config, today)),
        ]
        for name, fn in content_checks:
            ok = fn()
            status = "OK" if ok else "FAIL"
            results.append((name, ok))
            print(f"  [{status}] {name}")

    failures = [name for name, ok in results if not ok]
    if failures:
        print(f"\nFAILED: {', '.join(failures)}")
        from src.lib.alert import send_alert
        if config.alert_email_to:
            send_alert(
                template_name="alert_failure.j2",
                subject=f"[NewsBrief] Healthcheck FAILED - {today}",
                to_email=config.alert_email_to,
                from_email=config.alert_email_from,
                date=str(today),
                failed_stage="healthcheck",
                issue_number="N/A",
                duration="N/A",
                error_message=f"Failed checks: {', '.join(failures)}",
            )
        sys.exit(1)
    else:
        print("\nAll checks passed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
