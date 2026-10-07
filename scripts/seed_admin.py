"""Create the system's first ACTIVE Admin account out-of-band.

The last-ACTIVE-Admin invariant (spec FR-004e, FR-019d) means the API itself can never create the
first Admin, since every role/status change requires an already-authenticated Admin. Run this once
against a fresh database:

    python scripts/seed_admin.py <email> <password>
"""

from __future__ import annotations

import sys

from src.domain.models import AccountStatus, Role
from src.infrastructure.db.models import UserAccount
from src.infrastructure.db.session import SessionLocal
from src.infrastructure.security.hashing import hash_password


def seed_admin(email: str, password: str) -> None:
    db = SessionLocal()
    try:
        existing = db.query(UserAccount).filter(UserAccount.email == email).one_or_none()
        if existing is not None:
            print(
                f"Account {email} already exists (role={existing.role.value}); "
                "not creating a duplicate."
            )
            return

        admin = UserAccount(
            email=email,
            password_hash=hash_password(password),
            role=Role.ADMIN,
            status=AccountStatus.ACTIVE,
        )
        db.add(admin)
        db.commit()
        print(f"Seeded ACTIVE Admin account: {email}")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scripts/seed_admin.py <email> <password>")
        sys.exit(1)
    seed_admin(sys.argv[1], sys.argv[2])
