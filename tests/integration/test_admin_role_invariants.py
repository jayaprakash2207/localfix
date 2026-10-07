"""spec.md User Story 2a, Acceptance Scenarios 2 and 4 (FR-004b, FR-004d)."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.orm import Session as DBSession

from src.infrastructure.db.models import UserAccount
from tests.helpers import auth_headers, register_and_login


async def test_non_admin_role_change_attempt_is_denied(client: AsyncClient, db: DBSession):
    citizen_token = await register_and_login(client, "citizen@example.com")
    await register_and_login(client, "victim@example.com")
    victim = db.query(UserAccount).filter(UserAccount.email == "victim@example.com").one()

    resp = await client.patch(
        f"/admin/users/{victim.id}/role",
        json={"role": "officer"},
        headers=auth_headers(citizen_token),
    )
    assert resp.status_code == 403


async def test_admin_cannot_demote_self_even_as_sole_admin(
    client: AsyncClient, admin_token: str, db: DBSession
):
    admin = db.query(UserAccount).filter(UserAccount.email == "seed-admin@example.com").one()
    resp = await client.patch(
        f"/admin/users/{admin.id}/role", json={"role": "citizen"}, headers=auth_headers(admin_token)
    )
    assert resp.status_code == 403
    # Role must be unchanged.
    db.refresh(admin)
    assert admin.role.value == "admin"
