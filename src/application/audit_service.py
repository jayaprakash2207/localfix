"""Audit trail writer (spec FR-024–FR-026). Never accepts or persists a password value."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session as DBSession

from src.domain.models import AuditAction
from src.infrastructure.db.models import AuditRecord

_FORBIDDEN_DETAIL_KEYS = {"password", "password_hash", "new_password", "old_password"}


def record_event(
    db: DBSession,
    *,
    action: AuditAction,
    affected_user_id: uuid.UUID,
    actor_user_id: uuid.UUID | None,
    detail: dict | None = None,
) -> AuditRecord:
    if detail:
        leaked = _FORBIDDEN_DETAIL_KEYS & detail.keys()
        if leaked:
            raise ValueError(f"audit detail must not contain secret fields: {leaked}")

    record = AuditRecord(
        action=action.value,
        affected_user_id=affected_user_id,
        actor_user_id=actor_user_id,
        detail=detail,
    )
    db.add(record)
    db.flush()
    return record
