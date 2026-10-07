from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.orm import Session as DBSession

from tests.helpers import auth_headers, register_and_login


async def test_admin_can_change_role(client: AsyncClient, admin_token: str, db: DBSession):
    await register_and_login(client, "target@example.com")
    target = _get_user(db, "target@example.com")

    resp = await client.patch(
        f"/admin/users/{target.id}/role", json={"role": "officer"}, headers=auth_headers(admin_token)
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "officer"


async def test_non_admin_cannot_change_role(client: AsyncClient, db: DBSession):
    citizen_token = await register_and_login(client, "plain@example.com")
    target = _get_user(db, "plain@example.com")

    resp = await client.patch(
        f"/admin/users/{target.id}/role", json={"role": "officer"}, headers=auth_headers(citizen_token)
    )
    assert resp.status_code == 403


async def test_admin_self_demotion_is_forbidden(client: AsyncClient, admin_token: str, db: DBSession):
    admin = _get_user(db, "seed-admin@example.com")
    resp = await client.patch(
        f"/admin/users/{admin.id}/role", json={"role": "citizen"}, headers=auth_headers(admin_token)
    )
    assert resp.status_code == 403


async def test_one_admin_can_demote_a_different_admin(client: AsyncClient, admin_token: str, db: DBSession):
    # Promote a second user to Admin (actor is the seed admin, target is someone else - allowed).
    await register_and_login(client, "second@example.com")
    second = _get_user(db, "second@example.com")
    promote = await client.patch(
        f"/admin/users/{second.id}/role", json={"role": "admin"}, headers=auth_headers(admin_token)
    )
    assert promote.status_code == 200

    # The seed admin (still Active Admin) can now demote the OTHER admin back to citizen,
    # since the seed admin itself remains as an ACTIVE Admin after the change.
    demote = await client.patch(
        f"/admin/users/{second.id}/role", json={"role": "citizen"}, headers=auth_headers(admin_token)
    )
    assert demote.status_code == 200


async def test_invalid_role_value_is_422(client: AsyncClient, admin_token: str, db: DBSession):
    await register_and_login(client, "target2@example.com")
    target = _get_user(db, "target2@example.com")
    resp = await client.patch(
        f"/admin/users/{target.id}/role",
        json={"role": "superuser"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422


def _get_user(db: DBSession, email: str):
    from src.infrastructure.db.models import UserAccount

    return db.query(UserAccount).filter(UserAccount.email == email).one()
