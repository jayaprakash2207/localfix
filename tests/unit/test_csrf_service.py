from __future__ import annotations

from src.application import csrf_service


def test_generate_csrf_token_returns_nonempty_string():
    token = csrf_service.generate_csrf_token()
    assert isinstance(token, str)
    assert len(token) > 0


def test_verify_csrf_token_matching_values_succeeds():
    token = csrf_service.generate_csrf_token()
    assert csrf_service.verify_csrf_token(token, token) is True


def test_verify_csrf_token_mismatched_values_fails():
    assert csrf_service.verify_csrf_token("token-a", "token-b") is False


def test_verify_csrf_token_missing_cookie_value_fails():
    assert csrf_service.verify_csrf_token(None, "some-header-value") is False


def test_verify_csrf_token_missing_header_value_fails():
    assert csrf_service.verify_csrf_token("some-cookie-value", None) is False


def test_verify_csrf_token_both_missing_fails():
    assert csrf_service.verify_csrf_token(None, None) is False
