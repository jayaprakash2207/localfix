"""Feature 002 BE-010: send_password_reset_email must actually dispatch a message via SMTP
(not just log), containing the reset link, using the configured SMTP settings."""

from __future__ import annotations

import pytest

from src.infrastructure import email as email_module
from src.infrastructure.config import settings


class _FakeSMTP:
    sent_messages: list[object] = []
    login_calls: list[tuple[str, str]] = []

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def login(self, username: str, password: str) -> None:
        _FakeSMTP.login_calls.append((username, password))

    def send_message(self, message) -> None:
        _FakeSMTP.sent_messages.append(message)


@pytest.fixture(autouse=True)
def _reset_fake_smtp():
    _FakeSMTP.sent_messages = []
    _FakeSMTP.login_calls = []
    yield


def test_send_password_reset_email_dispatches_a_message_with_the_reset_link(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(email_module.smtplib, "SMTP", _FakeSMTP)

    email_module.send_password_reset_email(
        "alice@example.com", "https://localfix.example/reset?token=abc123"
    )

    assert len(_FakeSMTP.sent_messages) == 1
    sent = _FakeSMTP.sent_messages[0]
    assert sent["To"] == "alice@example.com"
    assert "https://localfix.example/reset?token=abc123" in sent.get_content()


def test_send_password_reset_email_authenticates_when_credentials_are_configured(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(email_module.smtplib, "SMTP", _FakeSMTP)
    monkeypatch.setattr(settings, "smtp_username", "test-user")
    monkeypatch.setattr(settings, "smtp_password", "test-pass")

    email_module.send_password_reset_email("bob@example.com", "https://localfix.example/reset")

    assert len(_FakeSMTP.login_calls) == 1


def test_send_password_reset_email_skips_auth_when_credentials_are_not_configured(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(email_module.smtplib, "SMTP", _FakeSMTP)
    monkeypatch.setattr(settings, "smtp_username", "")
    monkeypatch.setattr(settings, "smtp_password", "")

    email_module.send_password_reset_email("bob@example.com", "https://localfix.example/reset")

    assert len(_FakeSMTP.login_calls) == 0
