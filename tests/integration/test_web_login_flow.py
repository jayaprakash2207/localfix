"""Feature 002 US1 AC2: a web client that registers and logs in via POST /auth/session can
reach a protected endpoint using only the session cookie - no Authorization header at all."""

from __future__ import annotations

from httpx import AsyncClient

from tests.helpers import DEFAULT_PASSWORD


async def test_cookie_only_login_reaches_protected_endpoint(client: AsyncClient):
    register_resp = await client.post(
        "/auth/register", json={"email": "alice@example.com", "password": DEFAULT_PASSWORD}
    )
    assert register_resp.status_code == 201

    session_resp = await client.post(
        "/auth/session", json={"email": "alice@example.com", "password": DEFAULT_PASSWORD}
    )
    assert session_resp.status_code == 200

    me_resp = await client.get("/users/me")
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "alice@example.com"


async def test_no_cookie_and_no_bearer_is_unauthorized(client: AsyncClient):
    resp = await client.get("/users/me")
    assert resp.status_code == 401
