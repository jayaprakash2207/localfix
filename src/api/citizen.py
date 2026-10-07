"""Demonstration-only citizen-restricted endpoint, solely to prove/verify the role-gating
mechanism (FR-012). LocalFix's actual citizen business functionality is out of this feature's
scope (spec Assumptions)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.dependencies import require_citizen
from src.infrastructure.db.models import UserAccount

router = APIRouter(prefix="/citizen", tags=["citizen"])


@router.get("/ping")
def citizen_ping(current_user: UserAccount = Depends(require_citizen)) -> dict[str, str]:
    return {"status": "ok", "role": current_user.role.value}
