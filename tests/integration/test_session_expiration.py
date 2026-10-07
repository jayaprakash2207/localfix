"""spec.md User Story 4, Acceptance Scenario 2."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy.orm import Session as DBSession

from src.infrastructure.db.models import Session as SessionModel
from src.infrastructure.security.tokens import hash_token
from tests.helpers import auth_headers, register_and_login


async def test_expired_session_is_rejected_without_explicit_logout(
    client: AsyncClient, db: DBSession
):
    token = await register_and_login(client, "alice@example.com")

    # Force this session into the past, simulating its configured duration having elapsed,
    # without needing to actually wait out SESSION_DURATION_MINUTES in real time.
    session_row = db.query(SessionModel).filter(SessionModel.token_hash == hash_token(token)).one()
    session_row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()

    resp = await client.get("/users/me", headers=auth_headers(token))
    assert resp.status_code == 401
