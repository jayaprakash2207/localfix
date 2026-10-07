"""Security review F2/F3, spec FR-028/SC-013: password length bounds 8-128, no complexity rules."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.helpers import register_and_login


async def test_register_rejects_password_shorter_than_8(client: AsyncClient):
    resp = await client.post(
        "/auth/register", json={"email": "short@example.com", "password": "a" * 7}
    )
    assert resp.status_code == 422


async def test_register_accepts_password_of_exactly_8(client: AsyncClient):
    resp = await client.post(
        "/auth/register", json={"email": "min8@example.com", "password": "a" * 8}
    )
    assert resp.status_code == 201


async def test_register_accepts_password_of_exactly_128(client: AsyncClient):
    resp = await client.post(
        "/auth/register", json={"email": "max128@example.com", "password": "a" * 128}
    )
    assert resp.status_code == 201


async def test_register_rejects_password_longer_than_128(client: AsyncClient):
    resp = await client.post(
        "/auth/register", json={"email": "toolong@example.com", "password": "a" * 129}
    )
    assert resp.status_code == 422


async def test_password_reset_confirm_rejects_out_of_bounds_new_password(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    import src.application.password_reset_service as svc

    sent: list[str] = []
    monkeypatch.setattr(
        svc, "send_password_reset_email", lambda to, reset_link: sent.append(reset_link)
    )

    await register_and_login(client, "resetme@example.com")
    await client.post("/auth/password-reset/request", json={"email": "resetme@example.com"})

    from urllib.parse import parse_qs, urlparse

    token = parse_qs(urlparse(sent[0]).query)["token"][0]

    too_short = await client.post(
        "/auth/password-reset/confirm", json={"token": token, "new_password": "short"}
    )
    assert too_short.status_code == 422

    too_long = await client.post(
        "/auth/password-reset/confirm", json={"token": token, "new_password": "a" * 129}
    )
    assert too_long.status_code == 422
