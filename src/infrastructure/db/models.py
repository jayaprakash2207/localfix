"""SQLAlchemy ORM models (data access layer).

Fields/constraints per specs/001-auth-rbac/data-model.md.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.domain.models import AccountStatus, Role
from src.infrastructure.db.session import Base


class UserAccount(Base):
    __tablename__ = "user_accounts"
    __table_args__ = (
        # FR-029: email identity is case-insensitive; the application layer always normalizes
        # to lowercase before querying/inserting, and this functional index is the DB-layer
        # backstop against any future code path that doesn't (security review F4).
        Index("ix_user_accounts_email_lower", text("lower(email)"), unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[Role] = mapped_column(
        Enum(Role, name="role", native_enum=False, length=16), nullable=False, default=Role.CITIZEN
    )
    status: Mapped[AccountStatus] = mapped_column(
        Enum(AccountStatus, name="account_status", native_enum=False, length=16),
        nullable=False,
        default=AccountStatus.ACTIVE,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    sessions: Mapped[list[Session]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_accounts.id"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[UserAccount] = relationship(back_populates="sessions")


class AuditRecord(Base):
    __tablename__ = "audit_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_accounts.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    affected_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_accounts.id"), nullable=False, index=True
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    detail: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class PasswordResetRequest(Base):
    __tablename__ = "password_reset_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_accounts.id"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LoginAttemptRecord(Base):
    __tablename__ = "login_attempt_records"

    # No separate UniqueConstraint on user_id - it's already this table's primary key below,
    # which is already unique; an explicit extra constraint would be pure redundant noise.
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_accounts.id"), primary_key=True
    )
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RateLimitRecord(Base):
    """Per-source-IP, per-endpoint fixed-window request counter (spec FR-030). Mirrors
    LoginAttemptRecord's pattern - PostgreSQL-backed, no new infrastructure (security review
    F7)."""

    __tablename__ = "rate_limit_records"

    source_ip: Mapped[str] = mapped_column(String(45), primary_key=True)  # max IPv6 length
    endpoint: Mapped[str] = mapped_column(String(100), primary_key=True)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    request_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
