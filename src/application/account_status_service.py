"""Admin-driven account enable/disable and the last-ACTIVE-Admin invariant (spec FR-019a-d)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from src.application import audit_service
from src.domain.models import AccountStatus, AuditAction, Role
from src.infrastructure.db.models import Session as SessionModel
from src.infrastructure.db.models import UserAccount


class SelfStatusChangeNotAllowed(Exception):
    pass


class LastAdminInvariantViolation(Exception):
    pass


def _active_admin_count(db: DBSession, *, excluding_user_id: uuid.UUID | None = None) -> int:
    """Locks every currently ACTIVE Admin row (not just the ones left after excluding the
    target) so that two concurrent status-change requests targeting two *different* admins
    contend for the same lock and serialize correctly (security review F5 - see role_service's
    identical helper for the full race-scenario explanation)."""
    stmt = (
        select(UserAccount.id)
        .where(UserAccount.role == Role.ADMIN, UserAccount.status == AccountStatus.ACTIVE)
        .with_for_update()
    )
    admin_ids = db.scalars(stmt).all()
    if excluding_user_id is not None:
        return sum(1 for admin_id in admin_ids if admin_id != excluding_user_id)
    return len(admin_ids)


def change_status(
    db: DBSession, *, actor: UserAccount, target_user_id: uuid.UUID, new_status: AccountStatus
) -> UserAccount:
    target = db.get(UserAccount, target_user_id)
    if target is None:
        raise LookupError(target_user_id)

    if target.id == actor.id:
        raise SelfStatusChangeNotAllowed()

    if (
        new_status == AccountStatus.DISABLED
        and target.role == Role.ADMIN
        and target.status == AccountStatus.ACTIVE
    ):
        remaining = _active_admin_count(db, excluding_user_id=target.id)
        if remaining < 1:
            raise LastAdminInvariantViolation()

    target.status = new_status

    if new_status == AccountStatus.DISABLED:
        now = datetime.now(UTC)
        db.query(SessionModel).filter(
            SessionModel.user_id == target.id, SessionModel.revoked_at.is_(None)
        ).update({SessionModel.revoked_at: now})

    db.flush()

    action = (
        AuditAction.ACCOUNT_DISABLED
        if new_status == AccountStatus.DISABLED
        else AuditAction.ACCOUNT_ENABLED
    )
    audit_service.record_event(
        db,
        action=action,
        affected_user_id=target.id,
        actor_user_id=actor.id,
    )
    db.commit()
    return target
