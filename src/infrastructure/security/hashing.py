"""Argon2id password hashing/verification (research.md: OWASP-recommended for new passwords)."""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()

# Fixed dummy hash verified against when no real account exists, so a lookup miss costs the
# same as a real verification attempt (security review F1/FR-031: no timing side-channel).
_DUMMY_HASH = PasswordHasher().hash("dummy-password-for-constant-time-login")


def hash_password(plain_password: str) -> str:
    return _hasher.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, plain_password)
    except (VerificationError, InvalidHashError):
        # VerificationError (and its subclass VerifyMismatchError) covers a wrong password;
        # InvalidHashError covers a malformed/non-Argon2 hash string. Either way, verification
        # did not succeed (F11) - argon2-cffi doesn't give these two cases a common base class.
        return False


def verify_dummy_password(plain_password: str) -> None:
    """Pays the same Argon2 cost as a real verify_password() call, for the case where no
    account exists to verify against (F1/FR-031). The result is intentionally discarded."""
    verify_password(plain_password, _DUMMY_HASH)
