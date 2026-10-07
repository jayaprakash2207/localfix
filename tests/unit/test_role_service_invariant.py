"""Service-level test of the last-ACTIVE-Admin invariant (FR-004e), calling role_service
directly so the branch is exercised even though it is unreachable through the HTTP API once
self-demotion (FR-004d) is also enforced at that layer (see contract test_admin_role.py)."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session as DBSession

from src.application import role_service
from src.domain.models import Role
from tests.helpers import seed_user


def test_demoting_the_sole_admin_via_a_different_actor_violates_the_invariant(db: DBSession):
    sole_admin = seed_user(db, email="sole-admin@example.com", role=Role.ADMIN)
    other_actor = seed_user(db, email="other-actor@example.com", role=Role.CITIZEN)

    with pytest.raises(role_service.LastAdminInvariantViolation):
        role_service.change_role(
            db, actor=other_actor, target_user_id=sole_admin.id, new_role=Role.CITIZEN
        )


def test_demoting_one_of_two_admins_is_allowed(db: DBSession):
    admin_a = seed_user(db, email="admin-a@example.com", role=Role.ADMIN)
    admin_b = seed_user(db, email="admin-b@example.com", role=Role.ADMIN)

    updated = role_service.change_role(
        db, actor=admin_a, target_user_id=admin_b.id, new_role=Role.CITIZEN
    )
    assert updated.role == Role.CITIZEN
