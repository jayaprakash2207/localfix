"""spec.md User Story 2b, Acceptance Scenarios 2, 3, 4."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.orm import Session as DBSession

from src.infrastructure.db.models import UserAccount
from tests.helpers import auth_headers, register_and_login


async def test_non_admin_status_change_attempt_is_denied(client: AsyncClient, db: DBSession):
    officer_token_setup = await register_and_login(client, "officer@example.com")
    await register_and_login(client, "victim@example.com")
    victim = db.query(UserAccount).filter(UserAccount.email == "victim@example.com").one()

    resp = await client.patch(
        f"/admin/users/{victim.id}/status",
        json={"status": "disabled"},
        headers=auth_headers(officer_token_setup),
    )
    assert resp.status_code == 403


async def test_self_disable_denied_for_any_role_including_admin(
    client: AsyncClient, admin_token: str, db: DBSession
):
    admin = db.query(UserAccount).filter(UserAccount.email == "seed-admin@example.com").one()
    resp = await client.patch(
        f"/admin/users/{admin.id}/status", json={"status": "disabled"}, headers=auth_headers(admin_token)
    )
    assert resp.status_code == 403
    db.refresh(admin)
    assert admin.status.value == "active"


async def test_disabling_the_only_other_active_admin_still_allowed_when_actor_remains(
    client: AsyncClient, admin_token: str, db: DBSession
):
    """Sanity check for the last-admin invariant boundary: disabling a DIFFERENT admin is allowed
    as long as the acting Admin itself remains ACTIVE afterward (so the count never hits zero)."""
    await register_and_login(client, "second-admin@example.com")
    second = db.query(UserAccount).filter(UserAccount.email == "second-admin@example.com").one()
    promote = await client.patch(
        f"/admin/users/{second.id}/role", json={"role": "admin"}, headers=auth_headers(admin_token)
    )
    assert promote.status_code == 200

    disable = await client.patch(
        f"/admin/users/{second.id}/status", json={"status": "disabled"}, headers=auth_headers(admin_token)
    )
    assert disable.status_code == 200
