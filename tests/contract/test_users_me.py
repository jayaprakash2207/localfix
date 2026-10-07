from __future__ import annotations

from httpx import AsyncClient

from tests.helpers import auth_headers, register_and_login


async def test_get_own_profile_returns_caller_data_without_password(client: AsyncClient):
    token = await register_and_login(client, "alice@example.com")
    resp = await client.get("/users/me", headers=auth_headers(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "alice@example.com"
    assert body["role"] == "citizen"
    assert "password" not in body
    assert "password_hash" not in body


async def test_get_own_profile_without_session_is_401(client: AsyncClient):
    resp = await client.get("/users/me")
    assert resp.status_code == 401


async def test_get_own_profile_with_bogus_token_is_401(client: AsyncClient):
    resp = await client.get("/users/me", headers=auth_headers("not-a-real-token"))
    assert resp.status_code == 401
