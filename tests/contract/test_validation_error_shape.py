"""Security review F8: 422 responses must use the same {"error": "..."} shape as every other
error, not FastAPI's default verbose {"detail": [...]} body."""

from __future__ import annotations

from httpx import AsyncClient


async def test_malformed_email_422_matches_the_generic_error_shape(client: AsyncClient):
    resp = await client.post(
        "/auth/register", json={"email": "not-an-email", "password": "ValidPassword1"}
    )
    assert resp.status_code == 422
    assert resp.json() == {"error": "validation_error"}


async def test_password_too_short_422_matches_the_generic_error_shape(client: AsyncClient):
    resp = await client.post(
        "/auth/register", json={"email": "someone@example.com", "password": "short"}
    )
    assert resp.status_code == 422
    assert resp.json() == {"error": "validation_error"}
