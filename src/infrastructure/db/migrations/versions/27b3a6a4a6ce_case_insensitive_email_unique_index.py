"""case insensitive email unique index

Revision ID: 27b3a6a4a6ce
Revises: fbb0739eb787
Create Date: 2026-10-07 09:57:51.652520

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '27b3a6a4a6ce'
down_revision: str | Sequence[str] | None = 'fbb0739eb787'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Security review F4 / spec FR-029: case-insensitive email uniqueness, as DB-layer
    # defense-in-depth alongside the application-layer lowercasing in auth_service.py and
    # password_reset_service.py.
    #
    # NOTE: autogenerate also proposed `op.create_unique_constraint(None,
    # 'login_attempt_records', ['user_id'])`, picked up from a redundant UniqueConstraint on a
    # column that is already that table's primary key. Removed here (and from the ORM model)
    # as pure noise - it would have added no actual constraint beyond the existing PK.
    op.create_index(
        'ix_user_accounts_email_lower',
        'user_accounts',
        [sa.literal_column('lower(email)')],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_user_accounts_email_lower', table_name='user_accounts')
