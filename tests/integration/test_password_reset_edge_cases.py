"""spec.md User Story 5, Acceptance Scenarios 4-5; FR-010a, FR-010b."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session as DBSession

from src.infrastructure.db.models import PasswordResetRequest
from tests.helpers import DEFAULT_PASSWORD, register_and_login


async def test_unregistered_email_creates_no_request_and_sends_no_email(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, db: DBSession
):
    sent: list[str] = []
    import src.application.password_reset_service as svc

    monkeypatch.setattr(
        svc, "send_password_reset_email", lambda to, reset_link: sent.append(reset_link)
    )

    resp = await client.post("/auth/password-reset/request", json={"email": "ghost@example.com"})
    assert resp.status_code == 202
    assert sent == []
    assert db.query(PasswordResetRequest).count() == 0


async def test_second_request_invalidates_the_first(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    sent: list[str] = []
    import src.application.password_reset_service as svc

    monkeypatch.setattr(
        svc, "send_password_reset_email", lambda to, reset_link: sent.append(reset_link)
    )

    await register_and_login(client, "alice@example.com", DEFAULT_PASSWORD)

    await client.post("/auth/password-reset/request", json={"email": "alice@example.com"})
    first_token = parse_qs(urlparse(sent[0]).query)["token"][0]

    await client.post("/auth/password-reset/request", json={"email": "alice@example.com"})
    second_token = parse_qs(urlparse(sent[1]).query)["token"][0]

    stale_attempt = await client.post(
        "/auth/password-reset/confirm", json={"token": first_token, "new_password": "First123!"}
    )
    assert stale_attempt.status_code == 400

    fresh_attempt = await client.post(
        "/auth/password-reset/confirm", json={"token": second_token, "new_password": "Second1!"}
    )
    assert fresh_attempt.status_code == 200
