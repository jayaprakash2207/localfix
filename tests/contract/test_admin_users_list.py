"""Feature 002 BE-008/BE-009: GET /admin/users supports partial case-insensitive email search,
role filter, status filter, and pagination; returns only safe fields."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.orm import Session as DBSession

from src.domain.models import AccountStatus, Role
from tests.helpers import DEFAULT_PASSWORD, auth_headers, register_and_login, seed_user


async def _admin_token(client: AsyncClient, db: DBSession) -> str:
    admin = seed_user(db, email="admin@example.com", role=Role.ADMIN)
    resp = await client.post(
        "/auth/login", json={"email": admin.email, "password": DEFAULT_PASSWORD}
    )
    return resp.json()["session_token"]


async def test_search_matches_partial_case_insensitive_email(client: AsyncClient, db: DBSession):
    token = await _admin_token(client, db)
    seed_user(db, email="alice.wonderland@example.com")
    seed_user(db, email="bob@example.com")

    resp = await client.get(
        "/admin/users", params={"search": "WONDER"}, headers=auth_headers(token)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["email"] == "alice.wonderland@example.com"


async def test_role_filter_returns_only_matching_role(client: AsyncClient, db: DBSession):
    token = await _admin_token(client, db)
    seed_user(db, email="officer1@example.com", role=Role.OFFICER)
    seed_user(db, email="citizen1@example.com", role=Role.CITIZEN)

    resp = await client.get("/admin/users", params={"role": "officer"}, headers=auth_headers(token))
    assert resp.status_code == 200
    body = resp.json()
    assert all(item["role"] == "officer" for item in body["items"])
    assert any(item["email"] == "officer1@example.com" for item in body["items"])


async def test_status_filter_returns_only_matching_status(client: AsyncClient, db: DBSession):
    token = await _admin_token(client, db)
    seed_user(db, email="disabled1@example.com", status=AccountStatus.DISABLED)
    seed_user(db, email="active1@example.com", status=AccountStatus.ACTIVE)

    resp = await client.get(
        "/admin/users", params={"status": "disabled"}, headers=auth_headers(token)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert all(item["status"] == "disabled" for item in body["items"])
    assert any(item["email"] == "disabled1@example.com" for item in body["items"])


async def test_safe_fields_only_no_password_or_session_data(client: AsyncClient, db: DBSession):
    token = await _admin_token(client, db)
    seed_user(db, email="safe@example.com")

    resp = await client.get("/admin/users", headers=auth_headers(token))
    body = resp.json()
    item = next(i for i in body["items"] if i["email"] == "safe@example.com")
    assert set(item.keys()) == {"id", "email", "role", "status", "created_at"}


async def test_default_pagination_is_page_1_size_20(client: AsyncClient, db: DBSession):
    token = await _admin_token(client, db)

    resp = await client.get("/admin/users", headers=auth_headers(token))
    body = resp.json()
    assert body["page"] == 1
    assert body["page_size"] == 20


async def test_out_of_bounds_page_returns_422(client: AsyncClient, db: DBSession):
    token = await _admin_token(client, db)

    resp = await client.get("/admin/users", params={"page": 0}, headers=auth_headers(token))
    assert resp.status_code == 422


async def test_out_of_bounds_page_size_returns_422(client: AsyncClient, db: DBSession):
    token = await _admin_token(client, db)

    resp = await client.get("/admin/users", params={"page_size": 101}, headers=auth_headers(token))
    assert resp.status_code == 422


async def test_non_admin_caller_gets_403(client: AsyncClient):
    token = await register_and_login(client, "citizen@example.com")

    resp = await client.get("/admin/users", headers=auth_headers(token))
    assert resp.status_code == 403
