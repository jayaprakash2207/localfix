from __future__ import annotations

from httpx import AsyncClient

from tests.helpers import DEFAULT_PASSWORD, register_and_login


async def test_five_failed_attempts_lock_out_even_the_correct_password(client: AsyncClient):
    await register_and_login(client, "alice@example.com")

    for _ in range(5):
        resp = await client.post(
            "/auth/login", json={"email": "alice@example.com", "password": "wrong"}
        )
        assert resp.status_code == 401

    locked_out = await client.post(
        "/auth/login", json={"email": "alice@example.com", "password": DEFAULT_PASSWORD}
    )
    assert locked_out.status_code == 401
