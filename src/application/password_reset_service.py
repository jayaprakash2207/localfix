"""Self-service password reset (spec FR-010, FR-010a, FR-010b)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session as DBSession

from src.application import audit_service
from src.domain.models import AuditAction
from src.infrastructure.config import settings
from src.infrastructure.db.models import PasswordResetRequest, UserAccount
from src.infrastructure.email import send_password_reset_email
from src.infrastructure.security.hashing import hash_password
from src.infrastructure.security.tokens import generate_token, hash_token


class InvalidResetToken(Exception):
    pass


def request_reset(db: DBSession, *, email: str) -> None:
    """Identical outward behavior whether or not the email is registered (FR-010b): callers
    MUST NOT branch on this function's return value, since it never signals which case occurred."""
    normalized_email = email.strip().lower()  # FR-029: email identity is case-insensitive
    user = db.query(UserAccount).filter(UserAccount.email == normalized_email).one_or_none()
    if user is None:
        return

    # Invalidate any prior outstanding request for this user so only the newest one works
    # (FR-010a) - mark not-yet-used ones expired immediately.
    now = datetime.now(UTC)
    db.query(PasswordResetRequest).filter(
        PasswordResetRequest.user_id == user.id, PasswordResetRequest.used_at.is_(None)
    ).update({PasswordResetRequest.expires_at: now})

    raw_token = generate_token()
    reset_request = PasswordResetRequest(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        expires_at=now + timedelta(minutes=settings.password_reset_link_duration_minutes),
    )
    db.add(reset_request)

    audit_service.record_event(
        db,
        action=AuditAction.PASSWORD_RESET_REQUESTED,
        affected_user_id=user.id,
        actor_user_id=None,
    )
    db.commit()

    send_password_reset_email(user.email, reset_link=f"https://localfix.example/reset?token={raw_token}")


def confirm_reset(db: DBSession, *, raw_token: str, new_password: str) -> None:
    token_hash = hash_token(raw_token)
    reset_request = (
        db.query(PasswordResetRequest)
        .filter(PasswordResetRequest.token_hash == token_hash)
        .one_or_none()
    )
    now = datetime.now(UTC)
    if (
        reset_request is None
        or reset_request.used_at is not None
        or now >= reset_request.expires_at
    ):
        raise InvalidResetToken()

    user = db.get(UserAccount, reset_request.user_id)
    user.password_hash = hash_password(new_password)
    reset_request.used_at = now

    audit_service.record_event(
        db,
        action=AuditAction.PASSWORD_RESET_COMPLETED,
        affected_user_id=user.id,
        actor_user_id=user.id,
    )
    db.commit()
