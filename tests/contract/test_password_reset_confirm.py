from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest
from httpx import AsyncClient

from tests.helpers import DEFAULT_PASSWORD, register_and_login


async def _request_and_capture_token(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, email: str
) -> str:
    sent: list[str] = []
    import src.application.password_reset_service as svc

    monkeypatch.setattr(
        svc, "send_password_reset_email", lambda to, reset_link: sent.append(reset_link)
    )
    await client.post("/auth/password-reset/request", json={"email": email})
    link = sent[0]
    return parse_qs(urlparse(link).query)["token"][0]


async def test_confirm_with_valid_token_succeeds(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    await register_and_login(client, "alice@example.com", DEFAULT_PASSWORD)
    token = await _request_and_capture_token(client, monkeypatch, "alice@example.com")

    resp = await client.post(
        "/auth/password-reset/confirm", json={"token": token, "new_password": "N3wP@ssw0rd!"}
    )
    assert resp.status_code == 200


async def test_confirm_with_invalid_token_is_400(client: AsyncClient):
    resp = await client.post(
        "/auth/password-reset/confirm",
        json={"token": "not-a-real-token", "new_password": "ValidEnough1"},
    )
    assert resp.status_code == 400


async def test_confirm_with_already_used_token_is_400(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    await register_and_login(client, "alice@example.com", DEFAULT_PASSWORD)
    token = await _request_and_capture_token(client, monkeypatch, "alice@example.com")

    first = await client.post(
        "/auth/password-reset/confirm", json={"token": token, "new_password": "N3wP@ssw0rd!"}
    )
    assert first.status_code == 200

    second = await client.post(
        "/auth/password-reset/confirm", json={"token": token, "new_password": "AnotherOne1!"}
    )
    assert second.status_code == 400
