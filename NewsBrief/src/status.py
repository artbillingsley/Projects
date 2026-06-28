from __future__ import annotations

import argparse
from datetime import date, timedelta

from sqlalchemy import desc, text

from src.config import load_config
from src.lib.db import get_engine, get_session
from src.models import VideoRun, VideoUpload


def main():
    parser = argparse.ArgumentParser(description="NewsBrief Pipeline Status")
    parser.add_argument("--date", type=str, help="Show details for a specific date")
    parser.add_argument("--days", type=int, default=7, help="Show last N days (default: 7)")
    args = parser.parse_args()

    config = load_config()
    engine = get_engine(config)
    session = get_session(engine)

    try:
        if args.date:
            run_date = date.fromisoformat(args.date)
            run = session.query(VideoRun).filter(VideoRun.run_date == run_date).first()
            if not run:
                print(f"No run found for {run_date}")
                return

            print(f"\n{'='*60}")
            print(f"Run: {run.id} | Issue #{run.issue_number} | Status: {run.status}")
            print(f"Started: {run.started_at} | Completed: {run.completed_at}")
            print(f"Duration: {run.total_duration_s}s")
            print(f"\nStage Timings:")
            for stage in ["extract", "script", "audio", "spec", "render", "post", "archive"]:
                val = getattr(run, f"stage_{stage}_s", None)
                print(f"  {stage:>10}: {val or 'N/A'}s")

            if run.failed_stage:
                print(f"\nFailed: {run.failed_stage} -- {run.error_message}")

            uploads = session.query(VideoUpload).filter(VideoUpload.run_id == run.id).all()
            if uploads:
                print(f"\nUploads ({len(uploads)}):")
                for u in uploads:
                    status_icon = "OK" if u.status == "completed" else "FAIL"
                    print(f"  [{status_icon}] {u.platform:>22} {u.platform_url or u.error_message or ''}")

        else:
            cutoff = date.today() - timedelta(days=args.days)
            runs = (
                session.query(VideoRun)
                .filter(VideoRun.run_date >= cutoff)
                .order_by(desc(VideoRun.run_date))
                .all()
            )

            if not runs:
                print(f"No runs in the last {args.days} days.")
                return

            print(f"\n{'Date':<14} {'Issue':<8} {'Status':<12} {'Duration':<12} {'Uploads'}")
            print("-" * 65)
            for run in runs:
                uploads = session.query(VideoUpload).filter(
                    VideoUpload.run_id == run.id,
                    VideoUpload.status == "completed",
                ).count()
                total = session.query(VideoUpload).filter(VideoUpload.run_id == run.id).count()
                dur = f"{run.total_duration_s}s" if run.total_duration_s else "N/A"
                print(f"{run.run_date}    {run.issue_number:<8} {run.status:<12} {dur:<12} {uploads}/{total}")

    finally:
        session.close()


if __name__ == "__main__":
    main()
