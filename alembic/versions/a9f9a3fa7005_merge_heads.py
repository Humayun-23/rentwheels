"""merge heads

Revision ID: a9f9a3fa7005
Revises: 9a1b2c3d4e5f, aebdc1c38237
Create Date: 2026-05-17 19:25:44.217978

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9f9a3fa7005'
down_revision: Union[str, Sequence[str], None] = ('9a1b2c3d4e5f', 'aebdc1c38237')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
