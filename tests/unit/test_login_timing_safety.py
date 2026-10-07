"""Security review F1 / spec FR-031: the nonexistent-email login path must pay the same
Argon2 cost as the wrong-password path, so response timing can't reveal account existence.

Verified behaviorally (call tracking), not by wall-clock timing, which would be flaky in CI.
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session as DBSession

from src.application import auth_service
from tests.helpers import DEFAULT_PASSWORD, seed_user


def test_nonexistent_email_still_invokes_a_password_verification(
    db: DBSession, monkeypatch: pytest.MonkeyPatch
):
    calls: list[str] = []
    monkeypatch.setattr(
        auth_service,
        "verify_dummy_password",
        lambda password: calls.append("dummy"),
    )

    with pytest.raises(auth_service.InvalidCredentials):
        auth_service.login(db, email="nobody@example.com", password="whatever")

    assert calls == ["dummy"]


def test_existing_account_wrong_password_does_not_call_the_dummy_path(
    db: DBSession, monkeypatch: pytest.MonkeyPatch
):
    seed_user(db, email="alice@example.com")

    calls: list[str] = []
    monkeypatch.setattr(
        auth_service,
        "verify_dummy_password",
        lambda password: calls.append("dummy"),
    )

    with pytest.raises(auth_service.InvalidCredentials):
        auth_service.login(db, email="alice@example.com", password="wrong-password")

    assert calls == []


def test_existing_account_correct_password_still_succeeds(db: DBSession):
    seed_user(db, email="alice@example.com")
    result = auth_service.login(db, email="alice@example.com", password=DEFAULT_PASSWORD)
    assert result.raw_token
