"""Backfill inventory for existing bikes

Revision ID: 0003_backfill_bike_inventory
Revises: 0002_payment_refund_fields
Create Date: 2026-05-18 00:00:00.000000

"""
from alembic import op


revision = "0003_backfill_bike_inventory"
down_revision = "0002_payment_refund_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO bike_inventory (
            bike_id,
            shop_id,
            total_quantity,
            available_quantity,
            rented_quantity,
            created_at,
            updated_at
        )
        SELECT
            bikes.id,
            bikes.shop_id,
            1,
            1,
            0,
            NOW(),
            NOW()
        FROM bikes
        LEFT JOIN bike_inventory ON bike_inventory.bike_id = bikes.id
        WHERE bike_inventory.id IS NULL
        """
    )


def downgrade() -> None:
    pass
