"""Shared Pydantic request/response schemas (presentation layer)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from src.domain.models import AccountStatus, Role


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")  # silently ignore any client-supplied role (FR-003)

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)  # FR-028: no complexity rules beyond length


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    session_token: str
    expires_at: datetime


class UserPublic(BaseModel):
    id: uuid.UUID
    email: EmailStr
    role: Role
    status: AccountStatus
    created_at: datetime


class ErrorResponse(BaseModel):
    error: str


class RoleChangeRequest(BaseModel):
    role: Role


class RoleChangeResponse(BaseModel):
    id: uuid.UUID
    role: Role


class StatusChangeRequest(BaseModel):
    status: AccountStatus


class StatusChangeResponse(BaseModel):
    id: uuid.UUID
    status: AccountStatus


class PasswordResetRequestBody(BaseModel):
    email: EmailStr


class PasswordResetRequestResponse(BaseModel):
    message: str = "If that email is registered, a reset link has been sent."


class PasswordResetConfirmBody(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)  # FR-028


class PasswordResetConfirmResponse(BaseModel):
    message: str = "Password updated."


class AuditRecordPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor_user_id: uuid.UUID | None
    action: str
    affected_user_id: uuid.UUID
    occurred_at: datetime
    detail: dict | None


class AuditLogResponse(BaseModel):
    items: list[AuditRecordPublic]
