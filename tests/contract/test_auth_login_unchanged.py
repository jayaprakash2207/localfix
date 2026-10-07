"""Feature 002 BE-002/SC-002: POST /auth/login's request/response shape and behavior must be
byte-for-byte unchanged by the addition of the cookie-based POST /auth/session endpoint."""

from __future__ import annotations

from httpx import AsyncClient

from tests.helpers import DEFAULT_PASSWORD


async def test_login_still_returns_session_token_and_sets_no_cookies(client: AsyncClient):
    await client.post(
        "/auth/register", json={"email": "alice@example.com", "password": DEFAULT_PASSWORD}
    )
    resp = await client.post(
        "/auth/login", json={"email": "alice@example.com", "password": DEFAULT_PASSWORD}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"session_token", "expires_at"}
    assert body["session_token"]

    assert "session_id" not in client.cookies
    assert "csrf_token" not in client.cookies


async def test_login_wrong_password_still_returns_generic_401(client: AsyncClient):
    await client.post(
        "/auth/register", json={"email": "alice@example.com", "password": DEFAULT_PASSWORD}
    )
    resp = await client.post(
        "/auth/login", json={"email": "alice@example.com", "password": "wrong-password"}
    )
    assert resp.status_code == 401
    assert resp.json() == {"error": "invalid_credentials"}


async def test_bearer_token_from_login_still_authenticates_requests(client: AsyncClient):
    await client.post(
        "/auth/register", json={"email": "alice@example.com", "password": DEFAULT_PASSWORD}
    )
    login_resp = await client.post(
        "/auth/login", json={"email": "alice@example.com", "password": DEFAULT_PASSWORD}
    )
    token = login_resp.json()["session_token"]

    me_resp = await client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "alice@example.com"
