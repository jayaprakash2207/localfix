from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.helpers import DEFAULT_PASSWORD, register_and_login


async def test_request_for_registered_and_unregistered_email_look_identical(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    sent: list[tuple[str, str]] = []
    import src.application.password_reset_service as svc

    monkeypatch.setattr(svc, "send_password_reset_email", lambda to, reset_link: sent.append((to, reset_link)))

    await register_and_login(client, "alice@example.com", DEFAULT_PASSWORD)

    registered_resp = await client.post("/auth/password-reset/request", json={"email": "alice@example.com"})
    unregistered_resp = await client.post(
        "/auth/password-reset/request", json={"email": "nobody@example.com"}
    )

    assert registered_resp.status_code == 202
    assert unregistered_resp.status_code == 202
    assert registered_resp.json() == unregistered_resp.json()

    # Only the registered email actually triggered an email send.
    assert len(sent) == 1
    assert sent[0][0] == "alice@example.com"
