"""Self-profile endpoint, per contracts/auth-api.md. Never accepts a target user id — the subject
is always derived solely from the validated session (spec FR-007, FR-008; User Story 3)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.dependencies import get_current_user
from src.api.schemas import UserPublic
from src.infrastructure.db.models import UserAccount

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserPublic)
def get_own_profile(current_user: UserAccount = Depends(get_current_user)) -> UserAccount:
    return current_user
