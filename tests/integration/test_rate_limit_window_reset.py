"""spec.md FR-030 (security review F7): the rate-limit window must actually reset, so a
source IP blocked in one window can make requests again once the window has elapsed."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy.orm import Session as DBSession

from src.infrastructure.db.models import RateLimitRecord
from tests.helpers import DEFAULT_PASSWORD


async def test_blocked_source_ip_succeeds_again_after_the_window_elapses(
    client: AsyncClient, db: DBSession
):
    for i in range(5):
        resp = await client.post(
            "/auth/register",
            json={"email": f"window-user{i}@example.com", "password": DEFAULT_PASSWORD},
        )
        assert resp.status_code == 201

    still_blocked = await client.post(
        "/auth/register",
        json={"email": "window-user-blocked@example.com", "password": DEFAULT_PASSWORD},
    )
    assert still_blocked.status_code == 429

    record = (
        db.query(RateLimitRecord)
        .filter(RateLimitRecord.endpoint == "register")
        .one()
    )
    assert record.request_count == 5

    # Simulate the 15-minute window having elapsed, without waiting in real time.
    record.window_start = datetime.now(UTC) - timedelta(minutes=16)
    db.commit()

    after_window = await client.post(
        "/auth/register",
        json={"email": "window-user-after@example.com", "password": DEFAULT_PASSWORD},
    )
    assert after_window.status_code == 201

    db.refresh(record)
    assert record.request_count == 1
