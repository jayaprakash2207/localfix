"""Domain-level types shared across the authentication/RBAC feature.

Framework-free: no SQLAlchemy, FastAPI, or Pydantic imports here.
"""

from __future__ import annotations

import enum


class Role(enum.StrEnum):
    """Exactly three values. Exactly one role is assigned per account at any time
    (data-model.md: Role enum)."""

    CITIZEN = "citizen"
    OFFICER = "officer"
    ADMIN = "admin"


class AccountStatus(enum.StrEnum):
    """ACTIVE | DISABLED (data-model.md: AccountStatus enum)."""

    ACTIVE = "active"
    DISABLED = "disabled"


class AuditAction(enum.StrEnum):
    """Canonical set of auditable security-sensitive actions (spec FR-024)."""

    REGISTER = "REGISTER"
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILURE = "LOGIN_FAILURE"
    LOGOUT = "LOGOUT"
    PASSWORD_RESET_REQUESTED = "PASSWORD_RESET_REQUESTED"
    PASSWORD_RESET_COMPLETED = "PASSWORD_RESET_COMPLETED"
    ACCOUNT_ENABLED = "ACCOUNT_ENABLED"
    ACCOUNT_DISABLED = "ACCOUNT_DISABLED"
    ROLE_CHANGED = "ROLE_CHANGED"
