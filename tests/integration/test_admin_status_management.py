"""spec.md User Story 2b, Acceptance Scenario 1; FR-021."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.orm import Session as DBSession

from src.infrastructure.db.models import AuditRecord, UserAccount
from tests.helpers import auth_headers, register_and_login


async def test_disabling_account_revokes_its_sessions_and_writes_audit_records(
    client: AsyncClient, admin_token: str, db: DBSession
):
    target_token = await register_and_login(client, "target@example.com")
    target = db.query(UserAccount).filter(UserAccount.email == "target@example.com").one()

    # Session is valid before disablement.
    before = await client.get("/users/me", headers=auth_headers(target_token))
    assert before.status_code == 200

    disable = await client.patch(
        f"/admin/users/{target.id}/status", json={"status": "disabled"}, headers=auth_headers(admin_token)
    )
    assert disable.status_code == 200

    after = await client.get("/users/me", headers=auth_headers(target_token))
    assert after.status_code == 401

    enable = await client.patch(
        f"/admin/users/{target.id}/status", json={"status": "active"}, headers=auth_headers(admin_token)
    )
    assert enable.status_code == 200

    audit_actions = {
        row.action
        for row in db.query(AuditRecord).filter(AuditRecord.affected_user_id == target.id).all()
    }
    assert "ACCOUNT_DISABLED" in audit_actions
    assert "ACCOUNT_ENABLED" in audit_actions
