"""Feature 002 BE-014/BE-015: the trusted-proxy middleware only honors X-Forwarded-For from a
connecting peer explicitly listed in TRUSTED_PROXY_IPS, and always uses the rightmost value of
a comma-separated header - never the full header string as one IP."""

from __future__ import annotations

import pytest

from src.infrastructure.config import settings
from src.infrastructure.security.trusted_proxy import TrustedProxyMiddleware


def _make_scope(peer_ip: str, forwarded_for: str | None) -> dict:
    headers = []
    if forwarded_for is not None:
        headers.append((b"x-forwarded-for", forwarded_for.encode("latin-1")))
    return {"type": "http", "client": (peer_ip, 12345), "headers": headers}


async def _run_middleware(scope: dict) -> dict:
    captured_scope: dict = {}

    async def downstream_app(received_scope, receive, send):
        captured_scope.update(received_scope)

    async def receive():
        return {"type": "http.disconnect"}

    async def send(message):
        pass

    middleware = TrustedProxyMiddleware(downstream_app)
    await middleware(scope, receive, send)
    return captured_scope


@pytest.fixture(autouse=True)
def _restore_trusted_proxy_ips():
    original = settings.trusted_proxy_ips
    yield
    settings.trusted_proxy_ips = original


async def test_trusted_peer_single_value_header_rewrites_client():
    settings.trusted_proxy_ips = ["10.0.0.1"]
    scope = _make_scope("10.0.0.1", "203.0.113.5")

    result_scope = await _run_middleware(scope)

    assert result_scope["client"] == ("203.0.113.5", 12345)


async def test_trusted_peer_multi_value_header_uses_rightmost_value_only():
    settings.trusted_proxy_ips = ["10.0.0.1"]
    scope = _make_scope("10.0.0.1", "203.0.113.5, 198.51.100.9")

    result_scope = await _run_middleware(scope)

    assert result_scope["client"] == ("198.51.100.9", 12345)


async def test_untrusted_peer_header_is_ignored():
    settings.trusted_proxy_ips = ["10.0.0.1"]
    scope = _make_scope("203.0.113.99", "9.9.9.9")

    result_scope = await _run_middleware(scope)

    assert result_scope["client"] == ("203.0.113.99", 12345)


async def test_no_trusted_proxies_configured_header_is_always_ignored():
    settings.trusted_proxy_ips = []
    scope = _make_scope("10.0.0.1", "9.9.9.9")

    result_scope = await _run_middleware(scope)

    assert result_scope["client"] == ("10.0.0.1", 12345)
