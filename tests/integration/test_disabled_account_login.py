"""spec.md User Story 6, Acceptance Scenario 1; FR-020."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.orm import Session as DBSession

from src.infrastructure.db.models import UserAccount
from tests.helpers import DEFAULT_PASSWORD, auth_headers, register_and_login


async def test_disabled_account_login_fails_with_same_generic_error_as_wrong_password(
    client: AsyncClient, admin_token: str, db: DBSession
):
    await register_and_login(client, "target@example.com")
    target = db.query(UserAccount).filter(UserAccount.email == "target@example.com").one()

    disable = await client.patch(
        f"/admin/users/{target.id}/status", json={"status": "disabled"}, headers=auth_headers(admin_token)
    )
    assert disable.status_code == 200

    login_resp = await client.post(
        "/auth/login", json={"email": "target@example.com", "password": DEFAULT_PASSWORD}
    )
    assert login_resp.status_code == 401
    assert login_resp.json() == {"error": "invalid_credentials"}
