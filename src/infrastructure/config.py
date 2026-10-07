"""Environment-based settings (constitution: Security and Privacy — no secrets committed;
DB credentials and tunables come from the environment, never hard-coded)."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


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

    # Feature 002 BE-012/BE-013: no default - a missing value must fail startup loudly, same
    # philosophy as database_url above, since silently defaulting to an insecure cookie would
    # be worse than refusing to start.
    cookie_secure: bool

    # Feature 002 BE-014/BE-015: empty by default (fail-closed) - forwarded client-IP headers
    # are never honored unless the immediately connecting peer is explicitly listed here.
    trusted_proxy_ips: Annotated[list[str], NoDecode] = []

    @field_validator("trusted_proxy_ips", mode="before")
    @classmethod
    def _parse_trusted_proxy_ips(cls, value: object) -> list[str]:
        # Accept a plain comma-separated string from the environment (e.g. "10.0.0.1,10.0.0.2")
        # rather than requiring JSON-list syntax in a .env file.
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value  # type: ignore[return-value]

    # Feature 002 BE-010: real password-reset email delivery. No defaults - there is no safe
    # mail server to silently fall back to.
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_from_address: str

    @model_validator(mode="after")
    def _cookie_secure_fails_closed_in_production(self) -> Settings:
        # Feature 002 BE-013: a production deployment MUST NOT be able to silently start with
        # an insecure cookie configuration, even if cookie_secure was explicitly (mistakenly)
        # set to false rather than merely left unset.
        if self.environment == "production" and not self.cookie_secure:
            raise ValueError(
                "COOKIE_SECURE must be true when ENVIRONMENT=production "
                "(refusing to start with an insecure session cookie in production)"
            )
        return self


settings = Settings()
