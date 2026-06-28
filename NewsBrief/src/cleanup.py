# src/cleanup.py
"""Monthly cleanup: null remotion_spec JSON older than 90 days, delete old logs."""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import text

from src.config import load_config
from src.lib.db import get_engine, get_session

import structlog

log = structlog.get_logger()


def main():
    config = load_config()
    engine = get_engine(config)
    session = get_session(engine)

    cutoff = date.today() - timedelta(days=90)

    try:
        result = session.execute(
            text("UPDATE video_scripts SET remotion_spec = NULL WHERE created_at < :cutoff AND remotion_spec IS NOT NULL"),
            {"cutoff": cutoff},
        )
        session.commit()
        log.info("cleanup.specs_nulled", count=result.rowcount, cutoff=str(cutoff))
    finally:
        session.close()


if __name__ == "__main__":
    main()
