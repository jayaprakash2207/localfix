"""Admin-driven role changes and the last-ACTIVE-Admin invariant (spec FR-004a-e)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from src.application import audit_service
from src.domain.models import AccountStatus, AuditAction, Role
from src.infrastructure.db.models import UserAccount


class SelfDemotionNotAllowed(Exception):
    pass


class LastAdminInvariantViolation(Exception):
    pass


def _active_admin_count(db: DBSession, *, excluding_user_id: uuid.UUID | None = None) -> int:
    """Locks every currently ACTIVE Admin row (not just the ones left after excluding the
    target) so that two concurrent role-change requests targeting two *different* admins
    contend for the same lock and serialize correctly, instead of each computing "remaining
    admins excluding my own target" against a stale, unlocked snapshot (security review F5 -
    without this, two admins demoting each other at the same instant could both succeed and
    leave zero ACTIVE admins)."""
    stmt = (
        select(UserAccount.id)
        .where(UserAccount.role == Role.ADMIN, UserAccount.status == AccountStatus.ACTIVE)
        .with_for_update()
    )
    admin_ids = db.scalars(stmt).all()
    if excluding_user_id is not None:
        return sum(1 for admin_id in admin_ids if admin_id != excluding_user_id)
    return len(admin_ids)


def change_role(
    db: DBSession, *, actor: UserAccount, target_user_id: uuid.UUID, new_role: Role
) -> UserAccount:
    target = db.get(UserAccount, target_user_id)
    if target is None:
        raise LookupError(target_user_id)

    if target.id == actor.id and new_role != Role.ADMIN:
        raise SelfDemotionNotAllowed()

    if target.role == Role.ADMIN and new_role != Role.ADMIN:
        remaining = _active_admin_count(db, excluding_user_id=target.id)
        if remaining < 1:
            raise LastAdminInvariantViolation()

    previous_role = target.role
    target.role = new_role
    db.flush()

    audit_service.record_event(
        db,
        action=AuditAction.ROLE_CHANGED,
        affected_user_id=target.id,
        actor_user_id=actor.id,
        detail={"previous_role": previous_role.value, "new_role": new_role.value},
    )
    db.commit()
    return target
