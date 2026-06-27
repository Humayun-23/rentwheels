"""Add RentalOS database foundation

Revision ID: 7c3a91d4e8f2
Revises: b6d4f2a91c03
Create Date: 2026-06-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7c3a91d4e8f2"
down_revision: Union[str, Sequence[str], None] = "b6d4f2a91c03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "rental_staff",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("shop_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(), nullable=False, server_default="staff"),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shop_id", "user_id", name="uq_rental_staff_shop_user"),
    )
    op.create_index(op.f("ix_rental_staff_id"), "rental_staff", ["id"], unique=False)
    op.create_index(op.f("ix_rental_staff_shop_id"), "rental_staff", ["shop_id"], unique=False)
    op.create_index(op.f("ix_rental_staff_user_id"), "rental_staff", ["user_id"], unique=False)

    op.create_table(
        "rental_customers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("shop_id", sa.Integer(), nullable=False),
        sa.Column("phone_number", sa.String(), nullable=False),
        sa.Column("firstname", sa.String(), nullable=True),
        sa.Column("lastname", sa.String(), nullable=True),
        sa.Column("document_consent", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column("document_consent_at", sa.DateTime(), nullable=True),
        sa.Column("marketing_consent", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column("marketing_consent_at", sa.DateTime(), nullable=True),
        sa.Column("current_flag_status", sa.String(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shop_id", "phone_number", name="uq_rental_customers_shop_phone"),
    )
    op.create_index(op.f("ix_rental_customers_created_by_user_id"), "rental_customers", ["created_by_user_id"], unique=False)
    op.create_index(op.f("ix_rental_customers_id"), "rental_customers", ["id"], unique=False)
    op.create_index(op.f("ix_rental_customers_phone_number"), "rental_customers", ["phone_number"], unique=False)
    op.create_index(op.f("ix_rental_customers_shop_id"), "rental_customers", ["shop_id"], unique=False)

    op.create_table(
        "rental_customer_flags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("shop_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("flag_type", sa.String(), nullable=False),
        sa.Column("severity", sa.String(), nullable=False, server_default="info"),
        sa.Column("note", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default="true"),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["customer_id"], ["rental_customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rental_customer_flags_created_by_user_id"), "rental_customer_flags", ["created_by_user_id"], unique=False)
    op.create_index(op.f("ix_rental_customer_flags_customer_id"), "rental_customer_flags", ["customer_id"], unique=False)
    op.create_index(op.f("ix_rental_customer_flags_id"), "rental_customer_flags", ["id"], unique=False)
    op.create_index(op.f("ix_rental_customer_flags_shop_id"), "rental_customer_flags", ["shop_id"], unique=False)

    op.create_table(
        "rental_bookings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("shop_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("bike_id", sa.Integer(), nullable=False),
        sa.Column("staff_id", sa.Integer(), nullable=True),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("total_amount", sa.Integer(), nullable=True),
        sa.Column("advance_paid", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("balance_due", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("security_deposit", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["bike_id"], ["bikes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["rental_customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["staff_id"], ["rental_staff.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rental_bookings_bike_id"), "rental_bookings", ["bike_id"], unique=False)
    op.create_index(op.f("ix_rental_bookings_customer_id"), "rental_bookings", ["customer_id"], unique=False)
    op.create_index(op.f("ix_rental_bookings_end_time"), "rental_bookings", ["end_time"], unique=False)
    op.create_index(op.f("ix_rental_bookings_id"), "rental_bookings", ["id"], unique=False)
    op.create_index(op.f("ix_rental_bookings_shop_id"), "rental_bookings", ["shop_id"], unique=False)
    op.create_index(op.f("ix_rental_bookings_staff_id"), "rental_bookings", ["staff_id"], unique=False)
    op.create_index(op.f("ix_rental_bookings_start_time"), "rental_bookings", ["start_time"], unique=False)
    op.create_index(op.f("ix_rental_bookings_status"), "rental_bookings", ["status"], unique=False)

    op.create_table(
        "rental_booking_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("booking_id", sa.Integer(), nullable=False),
        sa.Column("document_type", sa.String(), nullable=False),
        sa.Column("file_url", sa.String(), nullable=False),
        sa.Column("file_name", sa.String(), nullable=True),
        sa.Column("content_type", sa.String(), nullable=True),
        sa.Column("uploaded_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["booking_id"], ["rental_bookings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rental_booking_documents_booking_id"), "rental_booking_documents", ["booking_id"], unique=False)
    op.create_index(op.f("ix_rental_booking_documents_id"), "rental_booking_documents", ["id"], unique=False)
    op.create_index(op.f("ix_rental_booking_documents_uploaded_by_user_id"), "rental_booking_documents", ["uploaded_by_user_id"], unique=False)

    op.create_table(
        "rental_handover_photos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("booking_id", sa.Integer(), nullable=False),
        sa.Column("image_url", sa.String(), nullable=False),
        sa.Column("location_permission_granted", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("location_accuracy_meters", sa.Integer(), nullable=True),
        sa.Column("location_address", sa.String(), nullable=True),
        sa.Column("captured_at", sa.DateTime(), nullable=True),
        sa.Column("uploaded_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["booking_id"], ["rental_bookings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rental_handover_photos_booking_id"), "rental_handover_photos", ["booking_id"], unique=False)
    op.create_index(op.f("ix_rental_handover_photos_id"), "rental_handover_photos", ["id"], unique=False)
    op.create_index(op.f("ix_rental_handover_photos_uploaded_by_user_id"), "rental_handover_photos", ["uploaded_by_user_id"], unique=False)

    op.create_table(
        "rental_payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("booking_id", sa.Integer(), nullable=False),
        sa.Column("payment_type", sa.String(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("method", sa.String(), nullable=True),
        sa.Column("reference_number", sa.String(), nullable=True),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.Column("received_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["booking_id"], ["rental_bookings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["received_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rental_payments_booking_id"), "rental_payments", ["booking_id"], unique=False)
    op.create_index(op.f("ix_rental_payments_id"), "rental_payments", ["id"], unique=False)
    op.create_index(op.f("ix_rental_payments_received_by_user_id"), "rental_payments", ["received_by_user_id"], unique=False)
    op.create_index(op.f("ix_rental_payments_status"), "rental_payments", ["status"], unique=False)

    op.create_table(
        "rental_booking_notes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("booking_id", sa.Integer(), nullable=False),
        sa.Column("note", sa.String(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["booking_id"], ["rental_bookings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rental_booking_notes_booking_id"), "rental_booking_notes", ["booking_id"], unique=False)
    op.create_index(op.f("ix_rental_booking_notes_created_by_user_id"), "rental_booking_notes", ["created_by_user_id"], unique=False)
    op.create_index(op.f("ix_rental_booking_notes_id"), "rental_booking_notes", ["id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_rental_booking_notes_id"), table_name="rental_booking_notes")
    op.drop_index(op.f("ix_rental_booking_notes_created_by_user_id"), table_name="rental_booking_notes")
    op.drop_index(op.f("ix_rental_booking_notes_booking_id"), table_name="rental_booking_notes")
    op.drop_table("rental_booking_notes")

    op.drop_index(op.f("ix_rental_payments_status"), table_name="rental_payments")
    op.drop_index(op.f("ix_rental_payments_received_by_user_id"), table_name="rental_payments")
    op.drop_index(op.f("ix_rental_payments_id"), table_name="rental_payments")
    op.drop_index(op.f("ix_rental_payments_booking_id"), table_name="rental_payments")
    op.drop_table("rental_payments")

    op.drop_index(op.f("ix_rental_handover_photos_uploaded_by_user_id"), table_name="rental_handover_photos")
    op.drop_index(op.f("ix_rental_handover_photos_id"), table_name="rental_handover_photos")
    op.drop_index(op.f("ix_rental_handover_photos_booking_id"), table_name="rental_handover_photos")
    op.drop_table("rental_handover_photos")

    op.drop_index(op.f("ix_rental_booking_documents_uploaded_by_user_id"), table_name="rental_booking_documents")
    op.drop_index(op.f("ix_rental_booking_documents_id"), table_name="rental_booking_documents")
    op.drop_index(op.f("ix_rental_booking_documents_booking_id"), table_name="rental_booking_documents")
    op.drop_table("rental_booking_documents")

    op.drop_index(op.f("ix_rental_bookings_status"), table_name="rental_bookings")
    op.drop_index(op.f("ix_rental_bookings_start_time"), table_name="rental_bookings")
    op.drop_index(op.f("ix_rental_bookings_staff_id"), table_name="rental_bookings")
    op.drop_index(op.f("ix_rental_bookings_shop_id"), table_name="rental_bookings")
    op.drop_index(op.f("ix_rental_bookings_id"), table_name="rental_bookings")
    op.drop_index(op.f("ix_rental_bookings_end_time"), table_name="rental_bookings")
    op.drop_index(op.f("ix_rental_bookings_customer_id"), table_name="rental_bookings")
    op.drop_index(op.f("ix_rental_bookings_bike_id"), table_name="rental_bookings")
    op.drop_table("rental_bookings")

    op.drop_index(op.f("ix_rental_customer_flags_shop_id"), table_name="rental_customer_flags")
    op.drop_index(op.f("ix_rental_customer_flags_id"), table_name="rental_customer_flags")
    op.drop_index(op.f("ix_rental_customer_flags_customer_id"), table_name="rental_customer_flags")
    op.drop_index(op.f("ix_rental_customer_flags_created_by_user_id"), table_name="rental_customer_flags")
    op.drop_table("rental_customer_flags")

    op.drop_index(op.f("ix_rental_customers_shop_id"), table_name="rental_customers")
    op.drop_index(op.f("ix_rental_customers_phone_number"), table_name="rental_customers")
    op.drop_index(op.f("ix_rental_customers_id"), table_name="rental_customers")
    op.drop_index(op.f("ix_rental_customers_created_by_user_id"), table_name="rental_customers")
    op.drop_table("rental_customers")

    op.drop_index(op.f("ix_rental_staff_user_id"), table_name="rental_staff")
    op.drop_index(op.f("ix_rental_staff_shop_id"), table_name="rental_staff")
    op.drop_index(op.f("ix_rental_staff_id"), table_name="rental_staff")
    op.drop_table("rental_staff")
