# tests/test_db.py
from unittest.mock import patch, MagicMock


def test_get_engine_creates_engine_from_config():
    from src.lib.db import get_engine
    from src.config import Config

    cfg = Config(
        db_host="localhost",
        db_port=3306,
        db_user="test",
        db_password="test",
        db_name="testdb",
        anthropic_api_key="sk-test",
    )
    engine = get_engine(cfg)
    assert "mysql+pymysql" in str(engine.url)
    assert "testdb" in str(engine.url)


def test_get_session_returns_session():
    from src.lib.db import get_engine, get_session
    from src.config import Config

    cfg = Config(
        db_host="localhost",
        db_port=3306,
        db_user="test",
        db_password="test",
        db_name="testdb",
        anthropic_api_key="sk-test",
    )
    engine = get_engine(cfg)
    session = get_session(engine)
    assert session is not None
    session.close()
