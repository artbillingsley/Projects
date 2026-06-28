# src/lib/db.py
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import Config


def get_engine(config: Config) -> Engine:
    return create_engine(
        config.db_url,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False,
    )


def get_session(engine: Engine) -> Session:
    factory = sessionmaker(bind=engine)
    return factory()
