# tests/test_config.py
import os
import pytest
from unittest.mock import patch


def test_config_loads_db_settings_from_env():
    env = {
        "DB_HOST": "localhost",
        "DB_PORT": "3306",
        "DB_USER": "testuser",
        "DB_PASSWORD": "testpass",
        "DB_NAME": "testdb",
        "ANTHROPIC_API_KEY": "sk-ant-test",
        "PUBLISH_MODE": "preview",
    }
    with patch.dict(os.environ, env, clear=False):
        from src.config import load_config

        cfg = load_config()
        assert cfg.db_host == "localhost"
        assert cfg.db_port == 3306
        assert cfg.db_user == "testuser"
        assert cfg.db_name == "testdb"
        assert cfg.anthropic_api_key == "sk-ant-test"
        assert cfg.publish_mode == "preview"


def test_config_defaults_publish_mode_to_preview():
    env = {
        "DB_HOST": "localhost",
        "DB_PORT": "3306",
        "DB_USER": "testuser",
        "DB_PASSWORD": "testpass",
        "DB_NAME": "testdb",
        "ANTHROPIC_API_KEY": "sk-ant-test",
    }
    with patch.dict(os.environ, env, clear=False):
        from src.config import load_config

        cfg = load_config()
        assert cfg.publish_mode == "preview"


def test_config_raises_on_missing_required_key():
    env = {"DB_HOST": "localhost"}  # missing most required keys
    with patch.dict(os.environ, env, clear=True):
        from src.config import load_config

        with pytest.raises(ValueError, match="DB_USER"):
            load_config()
