"""Feature 002 BE-012/BE-013: COOKIE_SECURE has no default and must fail startup loudly rather
than silently run a production deployment with an insecure session cookie."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.infrastructure.config import Settings

_REQUIRED_ENV = {
    "DATABASE_URL": "postgresql+psycopg://x@localhost/x",
    "SMTP_HOST": "localhost",
    "SMTP_PORT": "1025",
    "SMTP_USERNAME": "test",
    "SMTP_PASSWORD": "test",
    "SMTP_FROM_ADDRESS": "noreply@localfix.test",
}


def _set_required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in _REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)


def test_production_with_cookie_secure_false_raises(monkeypatch: pytest.MonkeyPatch):
    _set_required_env(monkeypatch)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("COOKIE_SECURE", "false")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_development_with_cookie_secure_false_constructs_successfully(
    monkeypatch: pytest.MonkeyPatch,
):
    _set_required_env(monkeypatch)
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("COOKIE_SECURE", "false")

    settings = Settings(_env_file=None)
    assert settings.cookie_secure is False


def test_production_with_cookie_secure_true_constructs_successfully(
    monkeypatch: pytest.MonkeyPatch,
):
    _set_required_env(monkeypatch)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("COOKIE_SECURE", "true")

    settings = Settings(_env_file=None)
    assert settings.cookie_secure is True


def test_cookie_secure_entirely_unset_raises_regardless_of_environment(
    monkeypatch: pytest.MonkeyPatch,
):
    _set_required_env(monkeypatch)
    monkeypatch.delenv("COOKIE_SECURE", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)
