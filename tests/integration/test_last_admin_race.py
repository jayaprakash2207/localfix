"""Security review F5, spec FR-004e/FR-019d: the last-ACTIVE-Admin invariant must hold even
when two different admins are demoted/disabled by two concurrent requests at the same instant.

Uses real threads and real DB connections (not a single-threaded manual interleave) because the
actual protection mechanism is a row lock that makes one transaction *block* until the other
commits - that blocking behavior can only be exercised with genuine concurrency.
"""

from __future__ import annotations

import threading

from sqlalchemy.orm import Session as DBSession

from src.application import account_status_service, role_service
from src.domain.models import AccountStatus, Role
from tests.conftest import TestSessionLocal
from tests.helpers import seed_user


def test_concurrent_role_demotions_of_the_only_two_admins_cannot_both_succeed(db: DBSession):
    admin_x = seed_user(db, email="admin-x@example.com", role=Role.ADMIN)
    admin_y = seed_user(db, email="admin-y@example.com", role=Role.ADMIN)
    x_id, y_id = admin_x.id, admin_y.id

    outcomes: dict[str, str] = {}
    barrier = threading.Barrier(2)

    def demote(label: str, actor_id, target_id) -> None:
        session = TestSessionLocal()
        try:
            actor = session.get(type(admin_x), actor_id)
            barrier.wait(timeout=5)
            role_service.change_role(
                session, actor=actor, target_user_id=target_id, new_role=Role.CITIZEN
            )
            outcomes[label] = "succeeded"
        except role_service.LastAdminInvariantViolation:
            outcomes[label] = "rejected"
        finally:
            session.close()

    t1 = threading.Thread(target=demote, args=("x_demotes_y", x_id, y_id))
    t2 = threading.Thread(target=demote, args=("y_demotes_x", y_id, x_id))
    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)

    assert set(outcomes.values()) != {"succeeded"}, (
        "both concurrent demotions succeeded - zero ACTIVE admins would remain"
    )

    remaining_active_admins = (
        db.query(type(admin_x))
        .filter(type(admin_x).role == Role.ADMIN, type(admin_x).status == AccountStatus.ACTIVE)
        .count()
    )
    assert remaining_active_admins >= 1


def test_concurrent_status_disables_of_the_only_two_admins_cannot_both_succeed(db: DBSession):
    admin_x = seed_user(db, email="admin-x2@example.com", role=Role.ADMIN)
    admin_y = seed_user(db, email="admin-y2@example.com", role=Role.ADMIN)
    x_id, y_id = admin_x.id, admin_y.id

    outcomes: dict[str, str] = {}
    barrier = threading.Barrier(2)

    def disable(label: str, actor_id, target_id) -> None:
        session = TestSessionLocal()
        try:
            actor = session.get(type(admin_x), actor_id)
            barrier.wait(timeout=5)
            account_status_service.change_status(
                session, actor=actor, target_user_id=target_id, new_status=AccountStatus.DISABLED
            )
            outcomes[label] = "succeeded"
        except account_status_service.LastAdminInvariantViolation:
            outcomes[label] = "rejected"
        finally:
            session.close()

    t1 = threading.Thread(target=disable, args=("x_disables_y", x_id, y_id))
    t2 = threading.Thread(target=disable, args=("y_disables_x", y_id, x_id))
    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)

    assert set(outcomes.values()) != {"succeeded"}, (
        "both concurrent disables succeeded - zero ACTIVE admins would remain"
    )

    remaining_active_admins = (
        db.query(type(admin_x))
        .filter(type(admin_x).role == Role.ADMIN, type(admin_x).status == AccountStatus.ACTIVE)
        .count()
    )
    assert remaining_active_admins >= 1
