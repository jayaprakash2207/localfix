"""Opaque token generation/hashing for session and password-reset-link tokens
(research.md: server-side revocable tokens, not JWTs).

The raw token is handed to the client exactly once (at login, or in the reset-link email) and is
never persisted; only its hash is stored, so a database leak does not expose usable tokens.
"""

from __future__ import annotations

import hashlib
import secrets


def generate_token() -> str:
    """URL-safe, high-entropy opaque token for a session or password-reset link."""
    return secrets.token_urlsafe(32)


def hash_token(raw_token: str) -> str:
    """Deterministic one-way hash used to look up a token by its hash (not a password,
    so a fast hash is appropriate here; the token itself already has 256 bits of entropy)."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
