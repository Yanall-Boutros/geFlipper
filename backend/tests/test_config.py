import importlib

import pytest

from app.core import config


@pytest.fixture
def reload_settings(monkeypatch):
    """Reload app.core.config under a patched environment, then restore it."""
    def reload(**env):
        for key in ("DB_USER", "DB_PASS", "DB_HOST", "DB_PORT", "DB_NAME", "USER_AGENT", "ENABLE_COLLECTORS"):
            monkeypatch.delenv(key, raising=False)
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        return importlib.reload(config).settings

    yield reload
    monkeypatch.undo()
    importlib.reload(config)


def test_defaults(reload_settings):
    settings = reload_settings()
    assert settings.DATABASE_URL == "postgresql+asyncpg://root:@localhost:5432/geflipper"
    assert settings.ENABLE_COLLECTORS is True
    assert settings.USER_AGENT.startswith("geFlipper")


def test_database_url_from_env(reload_settings):
    settings = reload_settings(DB_USER="app", DB_PASS="pw", DB_HOST="postgres-db", DB_PORT="6543", DB_NAME="prices")
    assert settings.DATABASE_URL == "postgresql+asyncpg://app:pw@postgres-db:6543/prices"


def test_password_is_url_escaped(reload_settings):
    settings = reload_settings(DB_PASS="p@ss/w:rd")
    assert settings.DB_PASS == "p%40ss%2Fw%3Ard"
    assert "p%40ss%2Fw%3Ard@localhost" in settings.DATABASE_URL


@pytest.mark.parametrize("value, expected", [("0", False), ("1", True), ("yes", True)])
def test_enable_collectors(reload_settings, value, expected):
    assert reload_settings(ENABLE_COLLECTORS=value).ENABLE_COLLECTORS is expected
