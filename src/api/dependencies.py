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

from src.application import rate_limit_service
from src.domain.models import AccountStatus, Role
from src.infrastructure.db.models import Session as SessionModel
from src.infrastructure.db.models import UserAccount
from src.infrastructure.db.session import get_db
from src.infrastructure.security.tokens import hash_token

bearer_scheme = HTTPBearer(auto_error=False)

_UNAUTHORIZED = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_session")


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: DBSession = Depends(get_db),
) -> UserAccount:
    if credentials is None:
        raise _UNAUTHORIZED

    token_hash = hash_token(credentials.credentials)
    session_row = db.query(SessionModel).filter(SessionModel.token_hash == token_hash).one_or_none()
    if session_row is None:
        raise _UNAUTHORIZED

    now = datetime.now(UTC)
    if session_row.revoked_at is not None or now >= session_row.expires_at:
        raise _UNAUTHORIZED

    user = db.get(UserAccount, session_row.user_id)
    if user is None or user.status != AccountStatus.ACTIVE:
        raise _UNAUTHORIZED

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
