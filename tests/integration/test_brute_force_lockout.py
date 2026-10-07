"""spec.md User Story 7, Acceptance Scenarios 1-3."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy.orm import Session as DBSession

from src.infrastructure.db.models import LoginAttemptRecord, UserAccount
from tests.helpers import DEFAULT_PASSWORD, register_and_login


async def test_lockout_then_cooldown_elapsed_then_success_resets_counter(
    client: AsyncClient, db: DBSession
):
    await register_and_login(client, "alice@example.com")
    user = db.query(UserAccount).filter(UserAccount.email == "alice@example.com").one()

    for _ in range(5):
        await client.post("/auth/login", json={"email": "alice@example.com", "password": "wrong"})

    attempt = db.get(LoginAttemptRecord, user.id)
    assert attempt.consecutive_failures == 5
    assert attempt.locked_until is not None

    still_locked = await client.post(
        "/auth/login", json={"email": "alice@example.com", "password": DEFAULT_PASSWORD}
    )
    assert still_locked.status_code == 401

    # Simulate the 15-minute cool-down having elapsed, without waiting in real time.
    attempt.locked_until = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()

    success = await client.post(
        "/auth/login", json={"email": "alice@example.com", "password": DEFAULT_PASSWORD}
    )
    assert success.status_code == 200

    db.refresh(attempt)
    assert attempt.consecutive_failures == 0
    assert attempt.locked_until is None
