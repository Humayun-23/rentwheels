"""Add refund tracking fields to payments

Revision ID: 0002_payment_refund_fields
Revises: 0001_initial
Create Date: 2026-05-18 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "0002_payment_refund_fields"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("payment", sa.Column("refund_id", sa.String(), nullable=True))
    op.add_column("payment", sa.Column("refunded_amount", sa.Integer(), nullable=False, server_default="0"))
    op.create_index("ix_payment_refund_id", "payment", ["refund_id"], unique=True)
    op.alter_column("payment", "refunded_amount", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_payment_refund_id", table_name="payment")
    op.drop_column("payment", "refunded_amount")
    op.drop_column("payment", "refund_id")
