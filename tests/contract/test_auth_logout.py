from __future__ import annotations

from httpx import AsyncClient

from tests.helpers import auth_headers, register_and_login


async def test_logout_returns_204_and_invalidates_the_session(client: AsyncClient):
    token = await register_and_login(client, "alice@example.com")

    logout_resp = await client.post("/auth/logout", headers=auth_headers(token))
    assert logout_resp.status_code == 204

    me = await client.get("/users/me", headers=auth_headers(token))
    assert me.status_code == 401
