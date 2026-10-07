"""Security review F4, spec FR-029/SC-015: email identity is case-insensitive."""

from __future__ import annotations

from httpx import AsyncClient

from tests.helpers import DEFAULT_PASSWORD


async def test_duplicate_registration_with_different_case_is_rejected(client: AsyncClient):
    first = await client.post(
        "/auth/register", json={"email": "Alice@Example.com", "password": DEFAULT_PASSWORD}
    )
    assert first.status_code == 201

    second = await client.post(
        "/auth/register", json={"email": "alice@example.com", "password": DEFAULT_PASSWORD}
    )
    assert second.status_code == 409


async def test_login_succeeds_regardless_of_case_used_at_registration_vs_login(
    client: AsyncClient,
):
    await client.post(
        "/auth/register", json={"email": "Bob@Example.com", "password": DEFAULT_PASSWORD}
    )

    login_different_case = await client.post(
        "/auth/login", json={"email": "bob@EXAMPLE.com", "password": DEFAULT_PASSWORD}
    )
    assert login_different_case.status_code == 200

    profile = await client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {login_different_case.json()['session_token']}"},
    )
    assert profile.json()["email"] == "bob@example.com"
