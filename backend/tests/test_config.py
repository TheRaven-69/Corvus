import pytest
from app.core.config import Settings

TEST_DATABASE_URL = "postgresql+psycopg://corvus:password@localhost:5432/corvus"
TEST_JWT_SECRET_KEY = "test-secret-key"


def test_settings_use_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CORVUS_APP_NAME", raising=False)
    monkeypatch.delenv("CORVUS_DEBUG", raising=False)
    monkeypatch.delenv("CORVUS_DATABASE_URL", raising=False)
    monkeypatch.delenv("CORVUS_JWT_SECRET_KEY", raising=False)
    monkeypatch.delenv("CORVUS_CORS_ORIGINS", raising=False)

    settings = Settings(
        database_url=TEST_DATABASE_URL,
        jwt_secret_key=TEST_JWT_SECRET_KEY,
        _env_file=None,
    )

    assert settings.app_name == "Corvus API"
    assert settings.debug is False
    assert settings.cors_origins == [
        "http://localhost:5173",
    ]


def test_settings_read_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CORVUS_DEBUG", "true")
    monkeypatch.setenv("CORVUS_DATABASE_URL", TEST_DATABASE_URL)
    monkeypatch.setenv(
        "CORVUS_JWT_SECRET_KEY",
        TEST_JWT_SECRET_KEY,
    )
    monkeypatch.setenv(
        "CORVUS_CORS_ORIGINS",
        '["http://localhost:3000", "https://corvus.example.com"]',
    )

    settings = Settings(_env_file=None)

    assert settings.debug is True
    assert settings.database_url == TEST_DATABASE_URL
    assert settings.jwt_secret_key.get_secret_value() == TEST_JWT_SECRET_KEY
    assert settings.cors_origins == [
        "http://localhost:3000",
        "https://corvus.example.com",
    ]
