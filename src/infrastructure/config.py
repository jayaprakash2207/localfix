"""Environment-based settings (constitution: Security and Privacy — no secrets committed;
DB credentials and tunables come from the environment, never hard-coded)."""

from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # No fallback default (security review F10): a missing DATABASE_URL must fail the app
    # startup loudly, never silently target an unintended local/dev database.
    database_url: str
    test_database_url: str | None = None

    # Security review F6: gates interactive API documentation (see src/main.py). Defaults to
    # "development" so local/test runs behave exactly as before this change.
    environment: Literal["development", "production"] = "development"

    session_duration_minutes: int = 60
    password_reset_link_duration_minutes: int = 30
    login_lockout_threshold: int = 5
    login_lockout_duration_minutes: int = 15

    # Security review F7: per-source-IP, per-endpoint rate limiting on /auth/register and
    # /auth/password-reset/request.
    rate_limit_threshold: int = 5
    rate_limit_window_minutes: int = 15


settings = Settings()
