"""Registration, login, and logout business logic (spec FR-001–FR-006)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DBSession

from src.application import audit_service
from src.domain.models import AccountStatus, AuditAction, Role
from src.infrastructure.config import settings
from src.infrastructure.db.models import LoginAttemptRecord, UserAccount
from src.infrastructure.db.models import Session as SessionModel
from src.infrastructure.security.hashing import (
    hash_password,
    verify_dummy_password,
    verify_password,
)
from src.infrastructure.security.tokens import generate_token, hash_token


class EmailAlreadyRegistered(Exception):
    pass


class InvalidCredentials(Exception):
    """Raised for any login failure. The API layer MUST map this to the same generic
    401 response regardless of the underlying reason (wrong password, disabled account,
    locked-out account) — FR-020."""


@dataclass
class LoginResult:
    raw_token: str
    expires_at: datetime


def register(db: DBSession, *, email: str, password: str) -> UserAccount:
    """Create a new account. Role is always CITIZEN/ACTIVE regardless of any other
    client-supplied value (FR-002, FR-003) — callers of this function cannot pass a role at all."""
    user = UserAccount(
        email=email.strip().lower(),  # FR-029: email identity is case-insensitive
        password_hash=hash_password(password),
        role=Role.CITIZEN,
        status=AccountStatus.ACTIVE,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise EmailAlreadyRegistered(email) from exc

    audit_service.record_event(
        db,
        action=AuditAction.REGISTER,
        affected_user_id=user.id,
        actor_user_id=None,
    )
    db.commit()
    return user


def _record_failed_attempt(db: DBSession, user: UserAccount, now: datetime) -> None:
    attempt = db.get(LoginAttemptRecord, user.id)
    if attempt is None:
        attempt = LoginAttemptRecord(user_id=user.id, consecutive_failures=0)
        db.add(attempt)

    attempt.consecutive_failures += 1
    if attempt.consecutive_failures >= settings.login_lockout_threshold:
        attempt.locked_until = now + timedelta(minutes=settings.login_lockout_duration_minutes)


def login(db: DBSession, *, email: str, password: str) -> LoginResult:
    now = datetime.now(UTC)
    normalized_email = email.strip().lower()  # FR-029: email identity is case-insensitive
    user = db.query(UserAccount).filter(UserAccount.email == normalized_email).one_or_none()

    if user is not None:
        attempt = db.get(LoginAttemptRecord, user.id)
        if attempt is not None and attempt.locked_until is not None and now < attempt.locked_until:
            # Locked out: reject outright, regardless of credential correctness (FR-022).
            audit_service.record_event(
                db, action=AuditAction.LOGIN_FAILURE, affected_user_id=user.id, actor_user_id=None
            )
            db.commit()
            raise InvalidCredentials()

    if user is not None:
        credentials_ok = verify_password(password, user.password_hash)
        account_usable = user.status == AccountStatus.ACTIVE
    else:
        # No account to verify against - still pay the same Argon2 cost a real verification
        # would, so response timing can't distinguish "no such account" from "wrong password"
        # (security review F1/FR-031).
        verify_dummy_password(password)
        credentials_ok = False
        account_usable = False

    if not credentials_ok or not account_usable:
        # Same generic failure for wrong password AND a disabled account (FR-020) - never
        # disclose which condition caused the denial.
        if user is not None:
            _record_failed_attempt(db, user, now)
            audit_service.record_event(
                db,
                action=AuditAction.LOGIN_FAILURE,
                affected_user_id=user.id,
                actor_user_id=None,
            )
            db.commit()
        raise InvalidCredentials()

    attempt = db.get(LoginAttemptRecord, user.id)
    if attempt is not None:
        attempt.consecutive_failures = 0
        attempt.locked_until = None

    raw_token = generate_token()
    expires_at = now + timedelta(minutes=settings.session_duration_minutes)
    session_row = SessionModel(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        expires_at=expires_at,
    )
    db.add(session_row)
    audit_service.record_event(
        db,
        action=AuditAction.LOGIN_SUCCESS,
        affected_user_id=user.id,
        actor_user_id=user.id,
    )
    db.commit()
    return LoginResult(raw_token=raw_token, expires_at=expires_at)


def logout(db: DBSession, *, raw_token: str) -> None:
    token_hash = hash_token(raw_token)
    session_row = db.query(SessionModel).filter(SessionModel.token_hash == token_hash).one_or_none()
    if session_row is None:
        return

    session_row.revoked_at = datetime.now(UTC)
    audit_service.record_event(
        db,
        action=AuditAction.LOGOUT,
        affected_user_id=session_row.user_id,
        actor_user_id=session_row.user_id,
    )
    db.commit()
