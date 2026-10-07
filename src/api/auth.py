"""Public (unauthenticated) authentication endpoints, per contracts/auth-api.md."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session as DBSession

from src.api.dependencies import bearer_scheme, get_current_user, rate_limited
from src.api.schemas import (
    LoginRequest,
    LoginResponse,
    PasswordResetConfirmBody,
    PasswordResetConfirmResponse,
    PasswordResetRequestBody,
    PasswordResetRequestResponse,
    RegisterRequest,
    UserPublic,
)
from src.application import auth_service, password_reset_service
from src.infrastructure.db.models import UserAccount
from src.infrastructure.db.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limited("register"))],
)
def register(body: RegisterRequest, db: DBSession = Depends(get_db)) -> UserAccount:
    try:
        return auth_service.register(db, email=body.email, password=body.password)
    except auth_service.EmailAlreadyRegistered as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="email_already_registered"
        ) from exc


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, db: DBSession = Depends(get_db)) -> LoginResponse:
    try:
        result = auth_service.login(db, email=body.email, password=body.password)
    except auth_service.InvalidCredentials as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials"
        ) from exc
    return LoginResponse(session_token=result.raw_token, expires_at=result.expires_at)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    _current_user: UserAccount = Depends(get_current_user),  # 401s on an already-invalid session
    db: DBSession = Depends(get_db),
) -> None:
    auth_service.logout(db, raw_token=credentials.credentials)


@router.post(
    "/password-reset/request",
    response_model=PasswordResetRequestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(rate_limited("password_reset_request"))],
)
def request_password_reset(
    body: PasswordResetRequestBody, db: DBSession = Depends(get_db)
) -> PasswordResetRequestResponse:
    password_reset_service.request_reset(db, email=body.email)
    return PasswordResetRequestResponse()


@router.post("/password-reset/confirm", response_model=PasswordResetConfirmResponse)
def confirm_password_reset(
    body: PasswordResetConfirmBody, db: DBSession = Depends(get_db)
) -> PasswordResetConfirmResponse:
    try:
        password_reset_service.confirm_reset(
            db, raw_token=body.token, new_password=body.new_password
        )
    except password_reset_service.InvalidResetToken as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_reset_token"
        ) from exc
    return PasswordResetConfirmResponse()
