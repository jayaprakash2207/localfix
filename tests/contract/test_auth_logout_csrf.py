"""Feature 002 BE-004/BE-006/BE-007: cookie-authenticated logout requires a matching
X-CSRF-Token; bearer-authenticated logout is exempt (it cannot be forged cross-site)."""

from __future__ import annotations

from httpx import AsyncClient

from tests.helpers import DEFAULT_PASSWORD, auth_headers, register_and_login


async def test_cookie_logout_with_valid_csrf_token_succeeds_and_clears_cookies(
    client: AsyncClient,
):
    await client.post(
        "/auth/register", json={"email": "alice@example.com", "password": DEFAULT_PASSWORD}
    )
    await client.post(
        "/auth/session", json={"email": "alice@example.com", "password": DEFAULT_PASSWORD}
    )
    csrf_token = client.cookies["csrf_token"]

    resp = await client.post("/auth/logout", headers={"X-CSRF-Token": csrf_token})
    assert resp.status_code == 204

    me = await client.get("/users/me")
    assert me.status_code == 401


async def test_cookie_logout_with_missing_csrf_token_is_rejected(client: AsyncClient):
    await client.post(
        "/auth/register", json={"email": "alice@example.com", "password": DEFAULT_PASSWORD}
    )
    await client.post(
        "/auth/session", json={"email": "alice@example.com", "password": DEFAULT_PASSWORD}
    )

    resp = await client.post("/auth/logout")
    assert resp.status_code == 403
    assert resp.json() == {"error": "csrf_token_invalid"}


async def test_cookie_logout_with_mismatched_csrf_token_is_rejected(client: AsyncClient):
    await client.post(
        "/auth/register", json={"email": "alice@example.com", "password": DEFAULT_PASSWORD}
    )
    await client.post(
        "/auth/session", json={"email": "alice@example.com", "password": DEFAULT_PASSWORD}
    )

    resp = await client.post("/auth/logout", headers={"X-CSRF-Token": "wrong-token"})
    assert resp.status_code == 403
    assert resp.json() == {"error": "csrf_token_invalid"}


async def test_bearer_logout_succeeds_with_no_csrf_header(client: AsyncClient):
    token = await register_and_login(client, "bob@example.com")

    resp = await client.post("/auth/logout", headers=auth_headers(token))
    assert resp.status_code == 204
