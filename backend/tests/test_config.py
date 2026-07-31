import pytest

from app.core.config import Settings


def test_settings_use_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CORVUS_APP_NAME", raising=False)
    monkeypatch.delenv("CORVUS_DEBUG", raising=False)

    settings = Settings(_env_file=None)

    assert settings.app_name == "Corvus API"
    assert settings.debug is False


def test_settings_read_envirinment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CORVUS_DEBUG", "true")

    settings = Settings(_env_file=None)

    assert settings.debug is True
