from __future__ import annotations

from httpx import AsyncClient

from tests.helpers import DEFAULT_PASSWORD


async def test_login_success_returns_session_token_and_expiry(client: AsyncClient):
    await client.post(
        "/auth/register", json={"email": "alice@example.com", "password": DEFAULT_PASSWORD}
    )
    resp = await client.post(
        "/auth/login", json={"email": "alice@example.com", "password": DEFAULT_PASSWORD}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "session_token" in body and body["session_token"]
    assert "expires_at" in body


async def test_login_wrong_password_returns_generic_401(client: AsyncClient):
    await client.post(
        "/auth/register", json={"email": "alice@example.com", "password": DEFAULT_PASSWORD}
    )
    resp = await client.post(
        "/auth/login", json={"email": "alice@example.com", "password": "wrong-password"}
    )
    assert resp.status_code == 401
    assert resp.json() == {"error": "invalid_credentials"}


async def test_login_unknown_email_returns_generic_401(client: AsyncClient):
    resp = await client.post(
        "/auth/login", json={"email": "nobody@example.com", "password": DEFAULT_PASSWORD}
    )
    assert resp.status_code == 401
    assert resp.json() == {"error": "invalid_credentials"}
