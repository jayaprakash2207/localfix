"""Feature 002 BE-006/BE-007/SEC-004: cookie-authenticated calls to the admin role/status
endpoints require a matching X-CSRF-Token; bearer-authenticated calls are exempt."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.orm import Session as DBSession

from src.domain.models import Role
from tests.helpers import DEFAULT_PASSWORD, auth_headers, seed_user


async def _admin_cookie_session(client: AsyncClient, db: DBSession) -> None:
    seed_user(db, email="admin@example.com", role=Role.ADMIN)
    resp = await client.post(
        "/auth/session", json={"email": "admin@example.com", "password": DEFAULT_PASSWORD}
    )
    assert resp.status_code == 200


async def test_cookie_role_change_without_csrf_token_is_rejected(
    client: AsyncClient, db: DBSession
):
    await _admin_cookie_session(client, db)
    target = seed_user(db, email="target1@example.com")

    resp = await client.patch(f"/admin/users/{target.id}/role", json={"role": "officer"})
    assert resp.status_code == 403
    assert resp.json() == {"error": "csrf_token_invalid"}


async def test_cookie_role_change_with_mismatched_csrf_token_is_rejected(
    client: AsyncClient, db: DBSession
):
    await _admin_cookie_session(client, db)
    target = seed_user(db, email="target2@example.com")

    resp = await client.patch(
        f"/admin/users/{target.id}/role",
        json={"role": "officer"},
        headers={"X-CSRF-Token": "wrong-token"},
    )
    assert resp.status_code == 403
    assert resp.json() == {"error": "csrf_token_invalid"}


async def test_cookie_role_change_with_valid_csrf_token_succeeds(
    client: AsyncClient, db: DBSession
):
    await _admin_cookie_session(client, db)
    target = seed_user(db, email="target3@example.com")

    resp = await client.patch(
        f"/admin/users/{target.id}/role",
        json={"role": "officer"},
        headers={"X-CSRF-Token": client.cookies["csrf_token"]},
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "officer"


async def test_cookie_status_change_without_csrf_token_is_rejected(
    client: AsyncClient, db: DBSession
):
    await _admin_cookie_session(client, db)
    target = seed_user(db, email="target4@example.com")

    resp = await client.patch(f"/admin/users/{target.id}/status", json={"status": "disabled"})
    assert resp.status_code == 403
    assert resp.json() == {"error": "csrf_token_invalid"}


async def test_cookie_status_change_with_valid_csrf_token_succeeds(
    client: AsyncClient, db: DBSession
):
    await _admin_cookie_session(client, db)
    target = seed_user(db, email="target5@example.com")

    resp = await client.patch(
        f"/admin/users/{target.id}/status",
        json={"status": "disabled"},
        headers={"X-CSRF-Token": client.cookies["csrf_token"]},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "disabled"


async def test_bearer_role_change_succeeds_with_no_csrf_header(client: AsyncClient, db: DBSession):
    admin_user = seed_user(db, email="bearer-admin@example.com", role=Role.ADMIN)
    admin_bearer = await client.post(
        "/auth/login", json={"email": admin_user.email, "password": DEFAULT_PASSWORD}
    )
    admin_token = admin_bearer.json()["session_token"]
    target = seed_user(db, email="bearer-target@example.com")

    resp = await client.patch(
        f"/admin/users/{target.id}/role",
        json={"role": "officer"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200


async def test_bearer_status_change_succeeds_with_no_csrf_header(
    client: AsyncClient, db: DBSession
):
    admin_user = seed_user(db, email="bearer-admin3@example.com", role=Role.ADMIN)
    admin_bearer = await client.post(
        "/auth/login", json={"email": admin_user.email, "password": DEFAULT_PASSWORD}
    )
    admin_token = admin_bearer.json()["session_token"]
    target = seed_user(db, email="bearer-target2@example.com")

    resp = await client.patch(
        f"/admin/users/{target.id}/status",
        json={"status": "disabled"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
