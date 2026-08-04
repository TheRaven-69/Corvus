import pytest
from app.core.config import Settings

TEST_DATABASE_URL = "postgresql+psycopg://corvus:password@localhost:5432/corvus"


def test_settings_use_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CORVUS_APP_NAME", raising=False)
    monkeypatch.delenv("CORVUS_DEBUG", raising=False)
    monkeypatch.delenv("CORVUS_DATABASE_URL", raising=False)

    settings = Settings(
        database_url=TEST_DATABASE_URL,
        _env_file=None,
    )

    assert settings.app_name == "Corvus API"
    assert settings.debug is False


def test_settings_read_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CORVUS_DEBUG", "true")
    monkeypatch.setenv("CORVUS_DATABASE_URL", TEST_DATABASE_URL)

    settings = Settings(_env_file=None)

    assert settings.debug is True
    assert settings.database_url == TEST_DATABASE_URL
