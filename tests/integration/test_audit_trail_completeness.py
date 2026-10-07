"""spec.md User Story 8, Acceptance Scenarios 1-2; FR-024, FR-025, FR-026."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session as DBSession

from src.infrastructure.db.models import UserAccount
from tests.helpers import DEFAULT_PASSWORD, auth_headers, register_and_login


async def test_every_security_sensitive_action_produces_an_audit_record(
    client: AsyncClient, admin_token: str, db: DBSession, monkeypatch: pytest.MonkeyPatch
):
    sent: list[str] = []
    import src.application.password_reset_service as svc

    monkeypatch.setattr(
        svc, "send_password_reset_email", lambda to, reset_link: sent.append(reset_link)
    )

    # REGISTER + LOGIN_SUCCESS
    token = await register_and_login(client, "alice@example.com", DEFAULT_PASSWORD)
    alice = db.query(UserAccount).filter(UserAccount.email == "alice@example.com").one()

    # LOGIN_FAILURE
    await client.post("/auth/login", json={"email": "alice@example.com", "password": "wrong"})

    # LOGOUT
    await client.post("/auth/logout", headers=auth_headers(token))

    # PASSWORD_RESET_REQUESTED + PASSWORD_RESET_COMPLETED
    await client.post("/auth/password-reset/request", json={"email": "alice@example.com"})
    reset_token = parse_qs(urlparse(sent[0]).query)["token"][0]
    await client.post(
        "/auth/password-reset/confirm", json={"token": reset_token, "new_password": "New1Pass!"}
    )

    # ROLE_CHANGED
    await client.patch(
        f"/admin/users/{alice.id}/role", json={"role": "officer"}, headers=auth_headers(admin_token)
    )

    # ACCOUNT_DISABLED + ACCOUNT_ENABLED
    await client.patch(
        f"/admin/users/{alice.id}/status", json={"status": "disabled"}, headers=auth_headers(admin_token)
    )
    await client.patch(
        f"/admin/users/{alice.id}/status", json={"status": "active"}, headers=auth_headers(admin_token)
    )

    log_resp = await client.get("/admin/audit-log", headers=auth_headers(admin_token))
    assert log_resp.status_code == 200
    items = log_resp.json()["items"]

    actions_seen = {item["action"] for item in items}
    expected = {
        "REGISTER",
        "LOGIN_SUCCESS",
        "LOGIN_FAILURE",
        "LOGOUT",
        "PASSWORD_RESET_REQUESTED",
        "PASSWORD_RESET_COMPLETED",
        "ROLE_CHANGED",
        "ACCOUNT_DISABLED",
        "ACCOUNT_ENABLED",
    }
    assert expected.issubset(actions_seen)

    for item in items:
        assert item["affected_user_id"] is not None
        assert item["occurred_at"] is not None
        assert "password" not in item
        assert "password_hash" not in item
