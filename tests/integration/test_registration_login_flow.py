"""spec.md User Story 1, Acceptance Scenarios 1-3."""

from __future__ import annotations

from httpx import AsyncClient

from tests.helpers import DEFAULT_PASSWORD, auth_headers


async def test_register_then_login_then_view_own_profile(client: AsyncClient):
    register_resp = await client.post(
        "/auth/register", json={"email": "newcitizen@example.com", "password": DEFAULT_PASSWORD}
    )
    assert register_resp.status_code == 201
    assert register_resp.json()["role"] == "citizen"
    assert register_resp.json()["status"] == "active"

    login_resp = await client.post(
        "/auth/login", json={"email": "newcitizen@example.com", "password": DEFAULT_PASSWORD}
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["session_token"]

    profile_resp = await client.get("/users/me", headers=auth_headers(token))
    assert profile_resp.status_code == 200
    profile = profile_resp.json()
    assert profile["email"] == "newcitizen@example.com"
    assert profile["role"] == "citizen"
