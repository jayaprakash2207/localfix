from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.orm import Session as DBSession

from src.infrastructure.db.models import UserAccount
from tests.helpers import auth_headers, register_and_login


async def test_admin_can_disable_and_enable_another_account(
    client: AsyncClient, admin_token: str, db: DBSession
):
    await register_and_login(client, "target@example.com")
    target = db.query(UserAccount).filter(UserAccount.email == "target@example.com").one()

    disable = await client.patch(
        f"/admin/users/{target.id}/status", json={"status": "disabled"}, headers=auth_headers(admin_token)
    )
    assert disable.status_code == 200
    assert disable.json()["status"] == "disabled"

    enable = await client.patch(
        f"/admin/users/{target.id}/status", json={"status": "active"}, headers=auth_headers(admin_token)
    )
    assert enable.status_code == 200
    assert enable.json()["status"] == "active"


async def test_non_admin_cannot_change_status(client: AsyncClient, db: DBSession):
    citizen_token = await register_and_login(client, "citizen@example.com")
    await register_and_login(client, "victim@example.com")
    victim = db.query(UserAccount).filter(UserAccount.email == "victim@example.com").one()

    resp = await client.patch(
        f"/admin/users/{victim.id}/status",
        json={"status": "disabled"},
        headers=auth_headers(citizen_token),
    )
    assert resp.status_code == 403


async def test_admin_cannot_disable_own_account(client: AsyncClient, admin_token: str, db: DBSession):
    admin = db.query(UserAccount).filter(UserAccount.email == "seed-admin@example.com").one()
    resp = await client.patch(
        f"/admin/users/{admin.id}/status", json={"status": "disabled"}, headers=auth_headers(admin_token)
    )
    assert resp.status_code == 403


async def test_invalid_status_value_is_422(client: AsyncClient, admin_token: str, db: DBSession):
    await register_and_login(client, "target2@example.com")
    target = db.query(UserAccount).filter(UserAccount.email == "target2@example.com").one()
    resp = await client.patch(
        f"/admin/users/{target.id}/status",
        json={"status": "archived"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422
