"""Security review F10: a missing DATABASE_URL must fail startup loudly, never silently fall
back to an insecure/unintended default."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.infrastructure.config import Settings


def test_settings_requires_database_url(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_defaults_to_development_environment(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://x@localhost/x")
    monkeypatch.setenv("COOKIE_SECURE", "false")
    monkeypatch.setenv("SMTP_HOST", "localhost")
    monkeypatch.setenv("SMTP_PORT", "1025")
    monkeypatch.setenv("SMTP_USERNAME", "test")
    monkeypatch.setenv("SMTP_PASSWORD", "test")
    monkeypatch.setenv("SMTP_FROM_ADDRESS", "noreply@localfix.test")
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    assert Settings(_env_file=None).environment == "development"
