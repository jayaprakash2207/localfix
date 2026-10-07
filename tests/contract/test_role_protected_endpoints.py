from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.orm import Session as DBSession

from src.infrastructure.db.models import UserAccount
from tests.helpers import auth_headers, login, register_and_login


async def test_citizen_ping_allows_citizen_and_blocks_others(client: AsyncClient, admin_token: str):
    citizen_token = await register_and_login(client, "citizen@example.com")

    ok = await client.get("/citizen/ping", headers=auth_headers(citizen_token))
    assert ok.status_code == 200

    blocked = await client.get("/citizen/ping", headers=auth_headers(admin_token))
    assert blocked.status_code == 403


async def test_officer_ping_allows_officer_and_blocks_others(
    client: AsyncClient, admin_token: str, db: DBSession
):
    citizen_token = await register_and_login(client, "officer-to-be@example.com")

    blocked = await client.get("/officer/ping", headers=auth_headers(citizen_token))
    assert blocked.status_code == 403

    target = db.query(UserAccount).filter(UserAccount.email == "officer-to-be@example.com").one()
    promote = await client.patch(
        f"/admin/users/{target.id}/role", json={"role": "officer"}, headers=auth_headers(admin_token)
    )
    assert promote.status_code == 200

    officer_token = await login(client, "officer-to-be@example.com")
    allowed = await client.get("/officer/ping", headers=auth_headers(officer_token))
    assert allowed.status_code == 200

    admin_blocked = await client.get("/officer/ping", headers=auth_headers(admin_token))
    assert admin_blocked.status_code == 403
