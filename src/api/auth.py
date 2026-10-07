"""Public (unauthenticated) authentication endpoints, per contracts/auth-api.md."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session as DBSession

from src.api.dependencies import (
    CSRF_COOKIE_NAME,
    SESSION_COOKIE_NAME,
    get_current_user,
    rate_limited,
    require_csrf,
)
from src.api.schemas import (
    LoginRequest,
    LoginResponse,
    PasswordResetConfirmBody,
    PasswordResetConfirmResponse,
    PasswordResetRequestBody,
    PasswordResetRequestResponse,
    RegisterRequest,
    UserPublic,
    WebSessionResponse,
)
from src.application import auth_service, csrf_service, password_reset_service
from src.infrastructure.config import settings
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


@router.post("/session", response_model=WebSessionResponse)
def login_session(
    body: LoginRequest, response: Response, db: DBSession = Depends(get_db)
) -> WebSessionResponse:
    """Feature 002 BE-001: the cookie-based counterpart to POST /auth/login. Reuses the same
    auth_service.login() so lockout/timing/audit behavior is identical - only the transport
    differs (cookies instead of a token in the response body)."""
    try:
        result = auth_service.login(db, email=body.email, password=body.password)
    except auth_service.InvalidCredentials as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials"
        ) from exc

    max_age = int((result.expires_at - datetime.now(UTC)).total_seconds())
    response.set_cookie(
        SESSION_COOKIE_NAME,
        result.raw_token,
        max_age=max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )
    response.set_cookie(
        CSRF_COOKIE_NAME,
        csrf_service.generate_csrf_token(),
        max_age=max_age,
        httponly=False,  # Feature 002 BE-005: must be readable by frontend JS to echo back
        secure=settings.cookie_secure,
        samesite="lax",
    )
    return WebSessionResponse(expires_at=result.expires_at)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    _current_user: UserAccount = Depends(get_current_user),  # 401s on an already-invalid session
    _csrf: None = Depends(require_csrf),  # only enforced for cookie-authenticated requests
    db: DBSession = Depends(get_db),
) -> None:
    auth_service.logout(db, raw_token=request.state.raw_token)
    response.delete_cookie(SESSION_COOKIE_NAME)
    response.delete_cookie(CSRF_COOKIE_NAME)


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
