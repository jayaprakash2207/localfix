"""ASGI middleware rewriting the connection's apparent client address from a trusted reverse
proxy's X-Forwarded-For header (Feature 002 BE-014/BE-015, spec SEC-005).

Fail-closed by construction: with an empty/unset TRUSTED_PROXY_IPS, forwarded headers are
never honored, and the system behaves exactly as it does without this middleware at all.
"""

from __future__ import annotations

from starlette.types import ASGIApp, Receive, Scope, Send

from src.infrastructure.config import settings


def _extract_forwarded_client_ip(header_value: str) -> str | None:
    """X-Forwarded-For may be a comma-separated chain (e.g. "203.0.113.5, 10.0.0.2") when
    multiple hops are involved. This feature's approved architecture has exactly one reverse
    proxy in front of the app, so the rightmost value - the address that proxy itself
    observed and appended - is used. The full header is never treated as a single opaque IP
    string (security review / Feature 002 pre-implementation check, point 4)."""
    parts = [part.strip() for part in header_value.split(",") if part.strip()]
    return parts[-1] if parts else None


class TrustedProxyMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not settings.trusted_proxy_ips:
            await self.app(scope, receive, send)
            return

        client = scope.get("client")
        connecting_peer = client[0] if client else None

        if connecting_peer not in settings.trusted_proxy_ips:
            # Not a trusted peer: never honor a forwarded-address claim from it, regardless
            # of what the header says (security review / Feature 002, points 2 and 3).
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        forwarded = headers.get(b"x-forwarded-for")
        if forwarded is not None:
            forwarded_ip = _extract_forwarded_client_ip(forwarded.decode("latin-1"))
            if forwarded_ip:
                port = client[1] if client else 0
                scope["client"] = (forwarded_ip, port)

        await self.app(scope, receive, send)
