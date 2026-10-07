"""spec.md User Story 1, Acceptance Scenario 4 and Edge Cases."""

from __future__ import annotations

from httpx import AsyncClient

from tests.helpers import DEFAULT_PASSWORD


async def test_duplicate_email_registration_is_rejected(client: AsyncClient):
    payload = {"email": "dup@example.com", "password": DEFAULT_PASSWORD}
    first = await client.post("/auth/register", json=payload)
    assert first.status_code == 201

    second = await client.post("/auth/register", json=payload)
    assert second.status_code == 409
    assert "password" not in second.text.lower().replace("password_hash", "")


async def test_forged_role_and_status_fields_are_ignored(client: AsyncClient):
    resp = await client.post(
        "/auth/register",
        json={
            "email": "forger@example.com",
            "password": DEFAULT_PASSWORD,
            "role": "admin",
            "status": "disabled",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["role"] == "citizen"
    assert body["status"] == "active"
