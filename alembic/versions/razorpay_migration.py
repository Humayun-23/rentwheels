"""razorpay_migration (DB-only head placeholder)

Revision ID: razorpay_migration
Revises: a9f9a3fa7005
Create Date: 2026-05-17 19:40:00.000000

This is a no-op placeholder migration to match the revision value
already present in the production `alembic_version` table. It links
the DB head to the repository's merge revision `a9f9a3fa7005` so
Alembic can resolve the revision graph.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'razorpay_migration'
down_revision: Union[str, Sequence[str], None] = 'a9f9a3fa7005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # No schema changes: placeholder to satisfy DB alembic_version
    pass


def downgrade() -> None:
    # No-op
    pass
