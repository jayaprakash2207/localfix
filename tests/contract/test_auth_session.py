from __future__ import annotations

from httpx import AsyncClient

from tests.helpers import DEFAULT_PASSWORD


async def test_session_login_success_sets_cookies_and_no_token_in_body(client: AsyncClient):
    await client.post(
        "/auth/register", json={"email": "alice@example.com", "password": DEFAULT_PASSWORD}
    )
    resp = await client.post(
        "/auth/session", json={"email": "alice@example.com", "password": DEFAULT_PASSWORD}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "expires_at" in body
    assert "session_token" not in body

    assert "session_id" in client.cookies
    assert "csrf_token" in client.cookies


async def test_session_login_wrong_password_returns_generic_401(client: AsyncClient):
    await client.post(
        "/auth/register", json={"email": "alice@example.com", "password": DEFAULT_PASSWORD}
    )
    resp = await client.post(
        "/auth/session", json={"email": "alice@example.com", "password": "wrong-password"}
    )
    assert resp.status_code == 401
    assert resp.json() == {"error": "invalid_credentials"}


async def test_session_login_unknown_email_returns_generic_401(client: AsyncClient):
    resp = await client.post(
        "/auth/session", json={"email": "nobody@example.com", "password": DEFAULT_PASSWORD}
    )
    assert resp.status_code == 401
    assert resp.json() == {"error": "invalid_credentials"}
