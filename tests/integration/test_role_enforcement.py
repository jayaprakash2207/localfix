"""spec.md User Story 2, Acceptance Scenarios 1-5."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.orm import Session as DBSession

from src.infrastructure.db.models import UserAccount
from tests.helpers import auth_headers, login, register_and_login


async def test_each_role_reaches_only_its_own_functionality(
    client: AsyncClient, admin_token: str, db: DBSession
):
    citizen_token = await register_and_login(client, "citizen@example.com")

    # Scenario 1: Citizen succeeds at citizen functionality.
    assert (await client.get("/citizen/ping", headers=auth_headers(citizen_token))).status_code == 200

    # Scenario 2: Citizen is rejected for officer- and admin-only functionality, even via a
    # direct call that bypasses any client-side logic (there is no "official client" here at
    # all — httpx talks straight to the ASGI app, proving enforcement is backend-side).
    assert (await client.get("/officer/ping", headers=auth_headers(citizen_token))).status_code == 403
    citizen = db.query(UserAccount).filter(UserAccount.email == "citizen@example.com").one()
    assert (
        await client.patch(
            f"/admin/users/{citizen.id}/role",
            json={"role": "officer"},
            headers=auth_headers(citizen_token),
        )
    ).status_code == 403

    # Promote citizen to officer for scenario 3.
    await client.patch(
        f"/admin/users/{citizen.id}/role", json={"role": "officer"}, headers=auth_headers(admin_token)
    )
    officer_token = await login(client, "citizen@example.com")

    # Scenario 3: Officer succeeds at officer functionality, rejected for admin-only.
    assert (await client.get("/officer/ping", headers=auth_headers(officer_token))).status_code == 200
    assert (
        await client.patch(
            f"/admin/users/{citizen.id}/role",
            json={"role": "admin"},
            headers=auth_headers(officer_token),
        )
    ).status_code == 403

    # Scenario 4: Admin succeeds at administrative functionality.
    assert (
        await client.patch(
            f"/admin/users/{citizen.id}/role", json={"role": "admin"}, headers=auth_headers(admin_token)
        )
    ).status_code == 200
