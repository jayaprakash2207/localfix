"""Admin-only endpoints, per contracts/auth-api.md."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session as DBSession

from src.api.dependencies import require_admin, require_csrf
from src.api.schemas import (
    AuditLogResponse,
    RoleChangeRequest,
    RoleChangeResponse,
    StatusChangeRequest,
    StatusChangeResponse,
    UserListResponse,
)
from src.application import account_status_service, role_service, user_query_service
from src.domain.models import AccountStatus, Role
from src.infrastructure.db.models import AuditRecord, UserAccount
from src.infrastructure.db.session import get_db

router = APIRouter(prefix="/admin", tags=["admin"])


@router.patch("/users/{user_id}/role", response_model=RoleChangeResponse)
def change_role(
    user_id: uuid.UUID,
    body: RoleChangeRequest,
    actor: UserAccount = Depends(require_admin),
    _csrf: None = Depends(require_csrf),
    db: DBSession = Depends(get_db),
) -> UserAccount:
    try:
        return role_service.change_role(db, actor=actor, target_user_id=user_id, new_role=body.role)
    except role_service.SelfDemotionNotAllowed as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="self_demotion_not_allowed"
        ) from exc
    except role_service.LastAdminInvariantViolation as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="last_admin_invariant"
        ) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found") from exc


@router.get("/users", response_model=UserListResponse)
def list_users(
    search: str | None = Query(default=None),
    role: Role | None = Query(default=None),
    status: AccountStatus | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    actor: UserAccount = Depends(require_admin),
    db: DBSession = Depends(get_db),
) -> UserListResponse:
    items, total = user_query_service.list_users(
        db, search=search, role=role, status=status, page=page, page_size=page_size
    )
    return UserListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/audit-log", response_model=AuditLogResponse)
def get_audit_log(
    user_id: uuid.UUID | None = Query(default=None, description="Filter by affected_user_id"),
    action: str | None = Query(
        default=None, description="Filter by exact action, e.g. LOGIN_SUCCESS"
    ),
    since: datetime | None = Query(
        default=None, description="Only records at/after this timestamp"
    ),
    until: datetime | None = Query(
        default=None, description="Only records at/before this timestamp"
    ),
    actor: UserAccount = Depends(require_admin),
    db: DBSession = Depends(get_db),
) -> AuditLogResponse:
    query = db.query(AuditRecord)
    if user_id is not None:
        query = query.filter(AuditRecord.affected_user_id == user_id)
    if action is not None:
        query = query.filter(AuditRecord.action == action)
    if since is not None:
        query = query.filter(AuditRecord.occurred_at >= since)
    if until is not None:
        query = query.filter(AuditRecord.occurred_at <= until)

    rows = query.order_by(AuditRecord.occurred_at.desc()).limit(500).all()
    return AuditLogResponse(items=rows)


@router.patch("/users/{user_id}/status", response_model=StatusChangeResponse)
def change_status(
    user_id: uuid.UUID,
    body: StatusChangeRequest,
    actor: UserAccount = Depends(require_admin),
    _csrf: None = Depends(require_csrf),
    db: DBSession = Depends(get_db),
) -> UserAccount:
    try:
        return account_status_service.change_status(
            db, actor=actor, target_user_id=user_id, new_status=body.status
        )
    except account_status_service.SelfStatusChangeNotAllowed as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="self_status_change_not_allowed"
        ) from exc
    except account_status_service.LastAdminInvariantViolation as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="last_admin_invariant"
        ) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found") from exc
