"""spec.md User Story 4, Acceptance Scenario 1."""

from __future__ import annotations

from httpx import AsyncClient

from tests.helpers import auth_headers, register_and_login


async def test_login_then_logout_then_prior_session_rejected(client: AsyncClient):
    token = await register_and_login(client, "alice@example.com")

    before = await client.get("/users/me", headers=auth_headers(token))
    assert before.status_code == 200

    logout = await client.post("/auth/logout", headers=auth_headers(token))
    assert logout.status_code == 204

    after = await client.get("/users/me", headers=auth_headers(token))
    assert after.status_code == 401
