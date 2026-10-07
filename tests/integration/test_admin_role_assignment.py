"""spec.md User Story 2a, Acceptance Scenarios 1 and 3."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.orm import Session as DBSession

from src.infrastructure.db.models import AuditRecord, UserAccount
from tests.helpers import auth_headers, login, register_and_login


async def test_admin_promotes_citizen_and_it_takes_effect_immediately(
    client: AsyncClient, admin_token: str, db: DBSession
):
    await register_and_login(client, "promoteme@example.com")
    target = db.query(UserAccount).filter(UserAccount.email == "promoteme@example.com").one()

    resp = await client.patch(
        f"/admin/users/{target.id}/role", json={"role": "officer"}, headers=auth_headers(admin_token)
    )
    assert resp.status_code == 200

    # Next authentication enforces the NEW role.
    new_token = await login(client, "promoteme@example.com")
    me = await client.get("/users/me", headers=auth_headers(new_token))
    assert me.json()["role"] == "officer"

    audit_rows = db.query(AuditRecord).filter(AuditRecord.action == "ROLE_CHANGED").all()
    assert any(row.affected_user_id == target.id for row in audit_rows)
