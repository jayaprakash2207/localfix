"""spec.md User Story 5, Acceptance Scenarios 1-3."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest
from httpx import AsyncClient

from tests.helpers import DEFAULT_PASSWORD, register_and_login


async def test_full_reset_flow_old_password_stops_working_new_one_works(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    sent: list[str] = []
    import src.application.password_reset_service as svc

    monkeypatch.setattr(
        svc, "send_password_reset_email", lambda to, reset_link: sent.append(reset_link)
    )

    await register_and_login(client, "alice@example.com", DEFAULT_PASSWORD)

    request_resp = await client.post(
        "/auth/password-reset/request", json={"email": "alice@example.com"}
    )
    assert request_resp.status_code == 202
    token = parse_qs(urlparse(sent[0]).query)["token"][0]

    confirm_resp = await client.post(
        "/auth/password-reset/confirm", json={"token": token, "new_password": "BrandNew1!"}
    )
    assert confirm_resp.status_code == 200

    old_login = await client.post(
        "/auth/login", json={"email": "alice@example.com", "password": DEFAULT_PASSWORD}
    )
    assert old_login.status_code == 401

    new_login = await client.post(
        "/auth/login", json={"email": "alice@example.com", "password": "BrandNew1!"}
    )
    assert new_login.status_code == 200
