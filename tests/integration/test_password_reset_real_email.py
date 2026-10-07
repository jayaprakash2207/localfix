"""Feature 002: confirms Feature 001's single-use/expiring reset-token behavior (FR-010a) is
unchanged now that the real SMTP send path has replaced the log-only stub."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest
from httpx import AsyncClient

from src.infrastructure import email as email_module
from tests.helpers import register_and_login


class _CapturingSMTP:
    sent: list[object] = []

    def __init__(self, host: str, port: int):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def login(self, username: str, password: str) -> None:
        pass

    def send_message(self, message) -> None:
        _CapturingSMTP.sent.append(message)


@pytest.fixture(autouse=True)
def _capture_smtp(monkeypatch: pytest.MonkeyPatch):
    _CapturingSMTP.sent = []
    monkeypatch.setattr(email_module.smtplib, "SMTP", _CapturingSMTP)
    yield


def _reset_link_from_last_sent() -> str:
    message = _CapturingSMTP.sent[-1]
    body = message.get_content()
    for line in body.splitlines():
        if line.startswith("http"):
            return line.strip()
    raise AssertionError("no reset link found in sent email body")


async def test_reset_token_is_single_use_with_real_send_path(client: AsyncClient):
    await register_and_login(client, "alice@example.com")
    await client.post("/auth/password-reset/request", json={"email": "alice@example.com"})

    link = _reset_link_from_last_sent()
    token = parse_qs(urlparse(link).query)["token"][0]

    first = await client.post(
        "/auth/password-reset/confirm", json={"token": token, "new_password": "NewP@ssw0rd1"}
    )
    assert first.status_code == 200

    second = await client.post(
        "/auth/password-reset/confirm", json={"token": token, "new_password": "AnotherP@ss1"}
    )
    assert second.status_code == 400


async def test_requesting_a_new_reset_invalidates_the_previous_one(client: AsyncClient):
    await register_and_login(client, "bob@example.com")
    await client.post("/auth/password-reset/request", json={"email": "bob@example.com"})
    first_link = _reset_link_from_last_sent()
    first_token = parse_qs(urlparse(first_link).query)["token"][0]

    await client.post("/auth/password-reset/request", json={"email": "bob@example.com"})

    stale = await client.post(
        "/auth/password-reset/confirm",
        json={"token": first_token, "new_password": "NewP@ssw0rd1"},
    )
    assert stale.status_code == 400
