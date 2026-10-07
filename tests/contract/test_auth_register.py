from __future__ import annotations

from httpx import AsyncClient

from tests.helpers import DEFAULT_PASSWORD


async def test_register_returns_201_with_citizen_role_and_no_password(client: AsyncClient):
    resp = await client.post(
        "/auth/register", json={"email": "alice@example.com", "password": DEFAULT_PASSWORD}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["role"] == "citizen"
    assert "password" not in body
    assert "password_hash" not in body


async def test_register_ignores_client_supplied_role(client: AsyncClient):
    resp = await client.post(
        "/auth/register",
        json={"email": "bob@example.com", "password": DEFAULT_PASSWORD, "role": "admin"},
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "citizen"


async def test_register_duplicate_email_is_409(client: AsyncClient):
    payload = {"email": "carol@example.com", "password": DEFAULT_PASSWORD}
    first = await client.post("/auth/register", json=payload)
    assert first.status_code == 201

    second = await client.post("/auth/register", json=payload)
    assert second.status_code == 409


async def test_register_invalid_email_is_422(client: AsyncClient):
    resp = await client.post(
        "/auth/register", json={"email": "not-an-email", "password": DEFAULT_PASSWORD}
    )
    assert resp.status_code == 422


async def test_register_missing_password_is_422(client: AsyncClient):
    resp = await client.post("/auth/register", json={"email": "dave@example.com"})
    assert resp.status_code == 422
