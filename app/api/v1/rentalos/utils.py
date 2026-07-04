from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile, status, Response
from sqlalchemy import case, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.api.v1.oauth2 import get_current_user
from app.config import settings
from app.db.database import get_db
from app.db.models import (
    Bike,
    BikeInventory,
    Booking,
    RentalBooking,
    RentalBookingDocument,
    RentalBookingNote,
    RentalCustomer,
    RentalCustomerFlag,
    RentalHandoverPhoto,
    RentalPayment,
    RentalStaff,
    Shop,
    User,
)
from app.services.availability import (
    MAINTENANCE_STATUSES,
    ONLINE_CONFLICT_STATUSES,
    RENTALOS_CONFLICT_STATUSES,
    check_bike_availability_by_id,
    overlap_filter,
)
from app.services.rentalos_invoice_email import enqueue_rentalos_invoice_email
from app.schemas.rentalos import (
    CatalogVehicleResponse,
    RentalBookingCompleteRequest,
    RentalBookingCreate,
    RentalBookingDocumentResponse,
    RentalDashboardSummaryResponse,
    RentalBookingNoteCreate,
    RentalBookingNoteResponse,
    RentalBookingResponse,
    RentalCustomerCreate,
    RentalCustomerFlagCreate,
    RentalCustomerFlagResponse,
    RentalCustomerFlagSummary,
    RentalCustomerOut,
    RentalCustomerSearchResponse,
    RentalHandoverPhotoResponse,
    RentalOSAccessShop,
    RentalOSMeResponse,
    RentalPaymentCreate,
    RentalPaymentResponse,
    RentalStaffCreate,
    RentalStaffResponse,
    RentalStaffUpdate,
)
from app.utils import tz
from app.utils.rentalos_r2 import (
    build_rentalos_blob_name,
    upload_rentalos_blob,
    validate_rentalos_upload,
    generate_rentalos_presigned_url,
)
from app.utils.utils import hash_password


DOCUMENT_TYPES = {"driving_license", "id_proof"}
DOCUMENT_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
HANDOVER_PHOTO_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
PAYMENT_TYPES = {"advance", "balance", "security_deposit", "refund", "extra_charge"}
PAYMENT_STATUSES = {"pending", "partial", "paid", "refunded"}
PAYMENT_METHODS = {"cash", "upi", "card", "bank_transfer", "other"}
STAFF_ROLES = {"staff"}
OPEN_BOOKING_STATUSES = {"active", "confirmed"}
CLOSED_BOOKING_STATUSES = {"completed", "cancelled"}
CUSTOMER_FLAG_TYPES = {
    "good_customer",
    "normal_customer",
    "late_return",
    "payment_issue",
    "damage_issue",
    "document_issue",
    "watchlist",
    "blocked",
}
CUSTOMER_FLAG_SEVERITIES = {"info", "warning", "blocked"}
NEGATIVE_FLAG_TYPES = {
    "late_return",
    "payment_issue",
    "damage_issue",
    "document_issue",
    "watchlist",
    "blocked",
}


def get_user_rental_staff_membership(db: Session, user_id: int, shop_id: int) -> Optional[RentalStaff]:
    return (
        db.query(RentalStaff)
        .filter(
            RentalStaff.user_id == user_id,
            RentalStaff.shop_id == shop_id,
            RentalStaff.is_active == True,
        )
        .first()
    )


def get_rentalos_shop_access(db: Session, shop_id: int, current_user: User) -> tuple[Shop, Optional[RentalStaff]]:
    shop = db.query(Shop).filter(Shop.id == shop_id).first()
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shop with ID {shop_id} not found",
        )

    if shop.rentalos_subscription_status != "active":
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="rentalos_subscription_required",
        )

    if shop.owner_id == current_user.id:
        return shop, None

    staff = get_user_rental_staff_membership(db, current_user.id, shop_id)
    if staff:
        return shop, staff

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have access to this shop.",
    )


def assert_rentalos_shop_access(db: Session, shop_id: int, current_user: User) -> tuple[Shop, Optional[RentalStaff]]:
    return get_rentalos_shop_access(db, shop_id, current_user)


def assert_rentalos_owner_access(db: Session, shop_id: int, current_user: User) -> Shop:
    shop = db.query(Shop).filter(Shop.id == shop_id).first()
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shop with ID {shop_id} not found",
        )
    
    if shop.rentalos_subscription_status != "active":
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="rentalos_subscription_required",
        )

    if shop.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shop owners can manage staff.",
        )
    return shop


def get_accessible_rental_booking(db: Session, booking_id: int, current_user: User) -> RentalBooking:
    booking = db.query(RentalBooking).filter(RentalBooking.id == booking_id).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rental booking not found.",
        )
    assert_rentalos_shop_access(db, booking.shop_id, current_user)
    return booking


def get_accessible_rental_customer(db: Session, customer_id: int, current_user: User) -> RentalCustomer:
    customer = db.query(RentalCustomer).filter(RentalCustomer.id == customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rental customer not found.",
        )
    assert_rentalos_shop_access(db, customer.shop_id, current_user)
    return customer


def _validate_time_range(start_time: datetime, end_time: datetime) -> tuple[datetime, datetime]:
    start_time = tz.ensure_aware(start_time)
    end_time = tz.ensure_aware(end_time)
    if start_time >= end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking start time must be before end time.",
        )
    return start_time, end_time


def _validate_staff_role(role: str | None) -> str:
    if role not in STAFF_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid staff role.",
        )
    return role


def _staff_response(staff: RentalStaff) -> RentalStaffResponse:
    return RentalStaffResponse(
        id=staff.id,
        shop_id=staff.shop_id,
        user_id=staff.user_id,
        email=staff.user.email,
        firstname=staff.user.firstname,
        lastname=staff.user.lastname,
        phone_number=staff.user.phone_number,
        role=staff.role,
        is_active=staff.is_active,
        created_at=staff.created_at,
        updated_at=staff.updated_at,
    )


def _bike_image_url(bike: Bike) -> str | None:
    if bike.image:
        return bike.image[0].image_url
    return None


def _max_rentalos_upload_bytes() -> int:
    return settings.rentalos_max_upload_mb * 1024 * 1024


def _require_non_empty_note(note: str, message: str = "Note cannot be empty.") -> str:
    note = note.strip()
    if not note:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )
    return note


def _normalize_optional_email(email: str | None) -> str | None:
    if email is None:
        return None
    email = str(email).strip().lower()
    return email or None


def _infer_customer_flag_severity(flag_type: str) -> str:
    if flag_type == "blocked":
        return "blocked"
    if flag_type in NEGATIVE_FLAG_TYPES:
        return "warning"
    return "info"


def _validate_customer_flag(flag_type: str, severity: str | None, note: str | None) -> tuple[str, str]:
    if flag_type not in CUSTOMER_FLAG_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid customer flag type.",
        )
    if severity and severity not in CUSTOMER_FLAG_SEVERITIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid customer flag severity.",
        )
    if flag_type in NEGATIVE_FLAG_TYPES and not (note and note.strip()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A note is required for this customer flag.",
        )
    return flag_type, severity or _infer_customer_flag_severity(flag_type)


def _create_customer_flag(
    db: Session,
    customer: RentalCustomer,
    flag_type: str,
    severity: str,
    note: str,
    is_active: bool,
    current_user: User,
) -> RentalCustomerFlag:
    db_flag = RentalCustomerFlag(
        shop_id=customer.shop_id,
        customer_id=customer.id,
        flag_type=flag_type,
        severity=severity,
        note=note,
        is_active=is_active,
        created_by_user_id=current_user.id,
    )
    db.add(db_flag)
    if is_active:
        customer.current_flag_status = flag_type
    return db_flag


def _validate_payment(payment: RentalPaymentCreate) -> None:
    if payment.payment_type not in PAYMENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payment type.",
        )
    if payment.status not in PAYMENT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payment status.",
        )
    if payment.method and payment.method not in PAYMENT_METHODS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payment method.",
        )
    if payment.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment amount must be positive.",
        )


def _apply_payment_summary(booking: RentalBooking, payment: RentalPaymentCreate) -> None:
    if payment.payment_type == "advance" and payment.status == "paid":
        booking.advance_paid = (booking.advance_paid or 0) + payment.amount
    elif payment.payment_type == "balance" and payment.status == "paid":
        booking.balance_due = max((booking.balance_due or 0) - payment.amount, 0)
    elif payment.payment_type == "security_deposit" and payment.status == "paid":
        booking.security_deposit = (booking.security_deposit or 0) + payment.amount
    elif payment.payment_type == "refund" and payment.status in {"paid", "refunded"}:
        booking.security_deposit = max((booking.security_deposit or 0) - payment.amount, 0)
    elif payment.payment_type == "extra_charge" and payment.status == "paid" and booking.total_amount is not None:
        booking.total_amount += payment.amount


def _booking_conflict_counts_by_bike(
    db: Session,
    booking_model,
    bike_ids: list[int],
    conflict_statuses: set[str],
    start_time: datetime | None,
    end_time: datetime | None,
    now: datetime,
) -> dict[int, int]:
    if not bike_ids:
        return {}

    query = db.query(booking_model.bike_id, func.count(booking_model.id)).filter(
        booking_model.bike_id.in_(bike_ids),
        booking_model.status.in_(conflict_statuses),
    )
    if start_time and end_time:
        query = query.filter(overlap_filter(booking_model, start_time, end_time))
    else:
        query = query.filter(booking_model.end_time > now)

    return {bike_id: count for bike_id, count in query.group_by(booking_model.bike_id).all()}


def _catalog_availability_statuses(
    db: Session,
    bikes: list[Bike],
    start_time: datetime | None,
    end_time: datetime | None,
) -> dict[int, str]:
    statuses: dict[int, str] = {}
    candidate_bikes: list[Bike] = []

    for bike in bikes:
        if not bike.is_available:
            statuses[bike.id] = "unavailable"
        elif bike.maintenance_status in MAINTENANCE_STATUSES:
            statuses[bike.id] = "maintenance"
        else:
            candidate_bikes.append(bike)

    candidate_ids = [bike.id for bike in candidate_bikes]
    if not candidate_ids:
        return statuses

    inventory_counts = {
        bike_id: total_quantity
        for bike_id, total_quantity in (
            db.query(BikeInventory.bike_id, BikeInventory.total_quantity)
            .filter(BikeInventory.bike_id.in_(candidate_ids))
            .all()
        )
    }
    now = tz.now()
    rentalos_conflicts = _booking_conflict_counts_by_bike(
        db,
        RentalBooking,
        candidate_ids,
        RENTALOS_CONFLICT_STATUSES,
        start_time,
        end_time,
        now,
    )
    online_conflicts = _booking_conflict_counts_by_bike(
        db,
        Booking,
        candidate_ids,
        ONLINE_CONFLICT_STATUSES,
        start_time,
        end_time,
        now,
    )

    for bike in candidate_bikes:
        total_quantity = inventory_counts.get(bike.id, 1)
        conflict_count = rentalos_conflicts.get(bike.id, 0) + online_conflicts.get(bike.id, 0)
        statuses[bike.id] = "available" if total_quantity > 0 and conflict_count < total_quantity else "booked"

    return statuses


def _dashboard_day_windows(
    as_of: datetime | None,
    timezone_offset_minutes: int,
) -> tuple[datetime, datetime, datetime, datetime]:
    as_of_utc = tz.ensure_aware(as_of) if as_of else tz.now()
    client_tz = timezone(timedelta(minutes=-timezone_offset_minutes))
    local_now = as_of_utc.astimezone(client_tz)
    today_start_local = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_start_local = today_start_local + timedelta(days=1)
    yesterday_start_local = today_start_local - timedelta(days=1)

    return (
        as_of_utc,
        yesterday_start_local.astimezone(timezone.utc),
        today_start_local.astimezone(timezone.utc),
        tomorrow_start_local.astimezone(timezone.utc),
    )


def _count_rental_bookings(db: Session, *filters) -> int:
    return db.query(func.count(RentalBooking.id)).filter(*filters).scalar() or 0


def _sum_positive_rental_booking_field(db: Session, field, *filters) -> int:
    value = (
        db.query(func.coalesce(func.sum(case((field > 0, field), else_=0)), 0))
        .filter(*filters)
        .scalar()
    )
    return int(value or 0)


def _sum_rental_collection_for_window(db: Session, shop_id: int, start: datetime, end: datetime) -> int:
    payment_time = func.coalesce(RentalPayment.paid_at, RentalPayment.created_at)
    payment_total = (
        db.query(
            func.coalesce(
                func.sum(
                    case(
                        (
                            (RentalPayment.payment_type == "refund")
                            & RentalPayment.status.in_(("paid", "refunded")),
                            -RentalPayment.amount,
                        ),
                        (
                            (RentalPayment.payment_type != "refund")
                            & (RentalPayment.status == "paid"),
                            RentalPayment.amount,
                        ),
                        else_=0,
                    )
                ),
                0,
            )
        )
        .join(RentalBooking, RentalPayment.booking_id == RentalBooking.id)
        .filter(
            RentalBooking.shop_id == shop_id,
            RentalBooking.status != "cancelled",
            RentalPayment.status.in_(("paid", "refunded")),
            payment_time >= start,
            payment_time < end,
        )
        .scalar()
        or 0
    )

    advance_payments_by_booking = {
        booking_id: int(amount or 0)
        for booking_id, amount in (
            db.query(
                RentalPayment.booking_id,
                func.coalesce(func.sum(RentalPayment.amount), 0),
            )
            .join(RentalBooking, RentalPayment.booking_id == RentalBooking.id)
            .filter(
                RentalBooking.shop_id == shop_id,
                RentalPayment.payment_type == "advance",
                RentalPayment.status == "paid",
            )
            .group_by(RentalPayment.booking_id)
            .all()
        )
    }
    created_bookings = (
        db.query(RentalBooking.id, RentalBooking.advance_paid)
        .filter(
            RentalBooking.shop_id == shop_id,
            RentalBooking.status != "cancelled",
            RentalBooking.created_at >= start,
            RentalBooking.created_at < end,
            RentalBooking.advance_paid > 0,
        )
        .all()
    )
    initial_advance_total = sum(
        max((advance_paid or 0) - advance_payments_by_booking.get(booking_id, 0), 0)
        for booking_id, advance_paid in created_bookings
    )

    return int(payment_total + initial_advance_total)


def _latest_customer_note(db: Session, customer_id: int, shop_id: int) -> str | None:
    note = (
        db.query(RentalBookingNote)
        .join(RentalBooking, RentalBookingNote.booking_id == RentalBooking.id)
        .filter(
            RentalBooking.customer_id == customer_id,
            RentalBooking.shop_id == shop_id,
        )
        .order_by(RentalBookingNote.created_at.desc())
        .first()
    )
    return note.note if note else None


def _customer_search_response(db: Session, customer: RentalCustomer, phone_number: str) -> RentalCustomerSearchResponse:
    latest_flag = (
        db.query(RentalCustomerFlag)
        .filter(
            RentalCustomerFlag.customer_id == customer.id,
            RentalCustomerFlag.shop_id == customer.shop_id,
            RentalCustomerFlag.is_active == True,
        )
        .order_by(RentalCustomerFlag.created_at.desc())
        .first()
    )
    previous_booking_count = (
        db.query(RentalBooking)
        .filter(
            RentalBooking.customer_id == customer.id,
            RentalBooking.shop_id == customer.shop_id,
        )
        .count()
    )

    return RentalCustomerSearchResponse(
        found=True,
        phone_number=phone_number,
        id=customer.id,
        email=customer.email,
        firstname=customer.firstname,
        lastname=customer.lastname,
        current_flag_status=customer.current_flag_status,
        previous_booking_count=previous_booking_count,
        latest_flag=RentalCustomerFlagSummary.model_validate(latest_flag) if latest_flag else None,
        latest_note=_latest_customer_note(db, customer.id, customer.shop_id),
    )


