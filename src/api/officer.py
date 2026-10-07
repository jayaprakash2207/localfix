"""Demonstration-only officer-restricted endpoint, solely to prove/verify the role-gating
mechanism (FR-013). LocalFix's actual officer business functionality is out of this feature's
scope (spec Assumptions)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.dependencies import require_officer
from src.infrastructure.db.models import UserAccount

router = APIRouter(prefix="/officer", tags=["officer"])


@router.get("/ping")
def officer_ping(current_user: UserAccount = Depends(require_officer)) -> dict[str, str]:
    return {"status": "ok", "role": current_user.role.value}
