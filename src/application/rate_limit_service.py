"""Per-source-IP, per-endpoint rate limiting (spec FR-030), backed by PostgreSQL via a
fixed-window counter - no new infrastructure, mirroring auth_service's login-lockout pattern
(security review F7)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session as DBSession

from src.infrastructure.config import settings
from src.infrastructure.db.models import RateLimitRecord


class RateLimitExceeded(Exception):
    pass


def enforce(db: DBSession, *, source_ip: str, endpoint: str) -> None:
    """Record this request against (source_ip, endpoint)'s current fixed window; raise
    RateLimitExceeded if the configured threshold has already been reached within that window.
    Commits on every call, independent of whatever the caller does with `db` afterward."""
    now = datetime.now(UTC)
    record = db.get(RateLimitRecord, (source_ip, endpoint))

    if record is None:
        db.add(
            RateLimitRecord(
                source_ip=source_ip, endpoint=endpoint, window_start=now, request_count=1
            )
        )
        db.commit()
        return

    window_age = now - record.window_start
    if window_age > timedelta(minutes=settings.rate_limit_window_minutes):
        record.window_start = now
        record.request_count = 1
        db.commit()
        return

    if record.request_count >= settings.rate_limit_threshold:
        db.commit()
        raise RateLimitExceeded()

    record.request_count += 1
    db.commit()
