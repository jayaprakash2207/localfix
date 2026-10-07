"""Admin user search/filter/pagination (Feature 002 BE-008/BE-009)."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from src.domain.models import AccountStatus, Role
from src.infrastructure.db.models import UserAccount


def list_users(
    db: DBSession,
    *,
    search: str | None,
    role: Role | None,
    status: AccountStatus | None,
    page: int,
    page_size: int,
) -> tuple[list[UserAccount], int]:
    query = db.query(UserAccount)

    if search:
        # FR-029: email identity is case-insensitive, so search matches the same way.
        query = query.filter(func.lower(UserAccount.email).contains(search.strip().lower()))
    if role is not None:
        query = query.filter(UserAccount.role == role)
    if status is not None:
        query = query.filter(UserAccount.status == status)

    total = query.count()
    items = (
        query.order_by(UserAccount.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total
