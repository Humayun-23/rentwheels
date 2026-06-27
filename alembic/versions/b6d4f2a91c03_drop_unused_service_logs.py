"""Drop unused service_logs table

Revision ID: b6d4f2a91c03
Revises: 42ee243ff209
Create Date: 2026-06-27 22:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b6d4f2a91c03"
down_revision: Union[str, Sequence[str], None] = "42ee243ff209"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop the maintenance service log table; this feature is not part of the product."""
    op.drop_index(op.f("ix_service_logs_id"), table_name="service_logs")
    op.drop_index(op.f("ix_service_logs_bike_id"), table_name="service_logs")
    op.drop_table("service_logs")


def downgrade() -> None:
    """Recreate service_logs if this cleanup migration is rolled back."""
    op.create_table(
        "service_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bike_id", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("cost", sa.Integer(), nullable=False),
        sa.Column("service_date", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["bike_id"], ["bikes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_service_logs_bike_id"), "service_logs", ["bike_id"], unique=False)
    op.create_index(op.f("ix_service_logs_id"), "service_logs", ["id"], unique=False)
