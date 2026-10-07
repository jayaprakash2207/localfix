"""Service-level test of the last-ACTIVE-Admin invariant for disablement (FR-019d)."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session as DBSession

from src.application import account_status_service
from src.domain.models import AccountStatus, Role
from tests.helpers import seed_user


def test_disabling_the_sole_admin_via_a_different_actor_violates_the_invariant(db: DBSession):
    sole_admin = seed_user(db, email="sole-admin@example.com", role=Role.ADMIN)
    other_actor = seed_user(db, email="other-actor@example.com", role=Role.CITIZEN)

    with pytest.raises(account_status_service.LastAdminInvariantViolation):
        account_status_service.change_status(
            db, actor=other_actor, target_user_id=sole_admin.id, new_status=AccountStatus.DISABLED
        )


def test_disabling_one_of_two_admins_is_allowed(db: DBSession):
    admin_a = seed_user(db, email="admin-a@example.com", role=Role.ADMIN)
    admin_b = seed_user(db, email="admin-b@example.com", role=Role.ADMIN)

    updated = account_status_service.change_status(
        db, actor=admin_a, target_user_id=admin_b.id, new_status=AccountStatus.DISABLED
    )
    assert updated.status == AccountStatus.DISABLED
