"""Cross-cutting FastAPI dependencies: session resolution and role-gating.

Every authenticated endpoint depends on get_current_user (directly or via require_role), which
re-validates the session per data-model.md's validity rule before any role check runs (spec FR-011,
FR-021, FR-023).
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session as DBSession

from src.application import csrf_service, rate_limit_service
from src.domain.models import AccountStatus, Role
from src.infrastructure.db.models import Session as SessionModel
from src.infrastructure.db.models import UserAccount
from src.infrastructure.db.session import get_db
from src.infrastructure.security.tokens import hash_token

bearer_scheme = HTTPBearer(auto_error=False)

SESSION_COOKIE_NAME = "session_id"
CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"

_UNAUTHORIZED = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_session")


def _resolve_session_token(
    request: Request, credentials: HTTPAuthorizationCredentials | None
) -> tuple[str, str] | None:
    """Returns (raw_token, transport) where transport is "bearer" or "cookie". The
    Authorization header is checked first (Feature 002 BE-003) so any client already sending
    one behaves exactly as before this feature existed."""
    if credentials is not None:
        return credentials.credentials, "bearer"
    cookie_token = request.cookies.get(SESSION_COOKIE_NAME)
    if cookie_token:
        return cookie_token, "cookie"
    return None


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: DBSession = Depends(get_db),
) -> UserAccount:
    resolved = _resolve_session_token(request, credentials)
    if resolved is None:
        raise _UNAUTHORIZED
    raw_token, transport = resolved

    token_hash = hash_token(raw_token)
    session_row = db.query(SessionModel).filter(SessionModel.token_hash == token_hash).one_or_none()
    if session_row is None:
        raise _UNAUTHORIZED

    now = datetime.now(UTC)
    if session_row.revoked_at is not None or now >= session_row.expires_at:
        raise _UNAUTHORIZED

    user = db.get(UserAccount, session_row.user_id)
    if user is None or user.status != AccountStatus.ACTIVE:
        raise _UNAUTHORIZED

    # Recorded so `require_csrf` can tell whether this request was cookie-authenticated
    # (CSRF-relevant) or bearer-authenticated (exempt) - Feature 002 BE-006/BE-007/SEC-004.
    # raw_token is recorded too so endpoints like logout can act on the session without
    # re-deriving which transport carried it.
    request.state.auth_transport = transport
    request.state.raw_token = raw_token
    return user


def require_role(*roles: Role):
    allowed = set(roles)

    def _check(user: UserAccount = Depends(get_current_user)) -> UserAccount:
        if user.role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
        return user

    return _check


require_admin = require_role(Role.ADMIN)
require_citizen = require_role(Role.CITIZEN)
require_officer = require_role(Role.OFFICER)


def rate_limited(endpoint_name: str):
    """FastAPI dependency factory enforcing spec FR-030 (security review F7) on an
    unauthenticated, public endpoint, keyed by source IP + the given logical endpoint name."""

    def _check(request: Request, db: DBSession = Depends(get_db)) -> None:
        source_ip = request.client.host if request.client is not None else "unknown"
        try:
            rate_limit_service.enforce(db, source_ip=source_ip, endpoint=endpoint_name)
        except rate_limit_service.RateLimitExceeded as exc:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="rate_limit_exceeded"
            ) from exc

    return _check


def require_csrf(
    request: Request,
    current_user: UserAccount = Depends(get_current_user),
) -> None:
    """Feature 002 BE-006/BE-007/SEC-004: only enforced when the request was authenticated via
    the session cookie (set by get_current_user on request.state.auth_transport). A
    bearer-authenticated request cannot be forged cross-site in the first place, so it is
    exempt - this is what keeps CSRF enforcement and the existing bearer contract compatible."""
    if getattr(request.state, "auth_transport", None) != "cookie":
        return

    cookie_value = request.cookies.get(CSRF_COOKIE_NAME)
    header_value = request.headers.get(CSRF_HEADER_NAME)
    if not csrf_service.verify_csrf_token(cookie_value, header_value):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="csrf_token_invalid")
