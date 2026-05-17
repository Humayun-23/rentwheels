"""add shop and bike images tables

Revision ID: 7b0b1c2f3a4d
Revises: e8ac63c34c59
Create Date: 2026-05-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7b0b1c2f3a4d"
down_revision: Union[str, Sequence[str], None] = "e8ac63c34c59"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "shop_images",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("shop_id", sa.Integer(), nullable=False),
        sa.Column("image_url", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_shop_images_id", "shop_images", ["id"], unique=False)
    op.create_index("ix_shop_images_shop_id", "shop_images", ["shop_id"], unique=False)

    op.create_table(
        "bike_images",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bike_id", sa.Integer(), nullable=False),
        sa.Column("image_url", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["bike_id"], ["bikes.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_bike_images_id", "bike_images", ["id"], unique=False)
    op.create_index("ix_bike_images_bike_id", "bike_images", ["bike_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_bike_images_bike_id", table_name="bike_images")
    op.drop_index("ix_bike_images_id", table_name="bike_images")
    op.drop_table("bike_images")

    op.drop_index("ix_shop_images_shop_id", table_name="shop_images")
    op.drop_index("ix_shop_images_id", table_name="shop_images")
    op.drop_table("shop_images")
