"""spec.md User Story 6, Acceptance Scenario 2; FR-021."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.orm import Session as DBSession

from src.infrastructure.db.models import UserAccount
from tests.helpers import auth_headers, register_and_login


async def test_existing_session_rejected_immediately_after_disablement(
    client: AsyncClient, admin_token: str, db: DBSession
):
    target_token = await register_and_login(client, "target@example.com")
    target = db.query(UserAccount).filter(UserAccount.email == "target@example.com").one()

    still_valid = await client.get("/users/me", headers=auth_headers(target_token))
    assert still_valid.status_code == 200

    await client.patch(
        f"/admin/users/{target.id}/status", json={"status": "disabled"}, headers=auth_headers(admin_token)
    )

    rejected = await client.get("/users/me", headers=auth_headers(target_token))
    assert rejected.status_code == 401
