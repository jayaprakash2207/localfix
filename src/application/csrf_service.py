"""Double-submit-cookie CSRF protection (Feature 002 BE-005/BE-006, spec SEC-004).

No server-side storage: the security property this relies on is that only JavaScript running
on the same site could have read the `csrf_token` cookie to echo it back in a header, so
proving the header matches the cookie is sufficient - the server never needs to remember
what value it issued.
"""

from __future__ import annotations

import hmac

from src.infrastructure.security.tokens import generate_token


def generate_csrf_token() -> str:
    return generate_token()


def verify_csrf_token(cookie_value: str | None, header_value: str | None) -> bool:
    if not cookie_value or not header_value:
        return False
    return hmac.compare_digest(cookie_value, header_value)
