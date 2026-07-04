"""Add RentalOS customer email

Revision ID: 15b8f2c4d6a1
Revises: 7c3a91d4e8f2
Create Date: 2026-07-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "15b8f2c4d6a1"
down_revision: Union[str, Sequence[str], None] = "7c3a91d4e8f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("rental_customers", sa.Column("email", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("rental_customers", "email")
