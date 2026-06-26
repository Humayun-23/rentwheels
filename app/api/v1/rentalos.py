from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.api.v1.oauth2 import get_current_user
from app.config import settings
from app.db.database import get_db
from app.db.models import (
    Bike,
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
    check_bike_availability_by_id,
)
from app.schemas.rentalos import (
    CatalogVehicleResponse,
    RentalBookingCompleteRequest,
    RentalBookingCreate,
    RentalBookingDocumentResponse,
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
from app.utils.rentalos_azure_blob import (
    build_rentalos_blob_name,
    upload_rentalos_blob,
    validate_rentalos_upload,
)
from app.utils.utils import hash_password


router = APIRouter(prefix="/rentalos", tags=["rentalos"])

DOCUMENT_TYPES = {"driving_license", "id_proof"}
DOCUMENT_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
HANDOVER_PHOTO_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
PAYMENT_TYPES = {"advance", "balance", "security_deposit", "refund", "extra_charge"}
PAYMENT_STATUSES = {"pending", "partial", "paid", "refunded"}
PAYMENT_METHODS = {"cash", "upi", "card", "bank_transfer", "other"}
STAFF_ROLES = {"staff"}
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


def is_bike_available_for_rentalos(
    db: Session,
    bike_id: int,
    start_time: datetime,
    end_time: datetime,
) -> tuple[bool, str | None]:
    _, _, availability = check_bike_availability_by_id(db, bike_id, start_time, end_time)
    return availability.is_available, availability.reason


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
    return settings.azure_storage_rentalos_max_upload_mb * 1024 * 1024


def _require_non_empty_note(note: str, message: str = "Note cannot be empty.") -> str:
    note = note.strip()
    if not note:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )
    return note


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


def _availability_status(db: Session, bike: Bike, start_time: datetime | None, end_time: datetime | None) -> str:
    if not bike.is_available:
        return "unavailable"
    if bike.maintenance_status in MAINTENANCE_STATUSES:
        return "maintenance"

    if start_time and end_time:
        available, _ = is_bike_available_for_rentalos(db, bike.id, start_time, end_time)
        return "available" if available else "booked"

    now = tz.now()
    current_window_end = now + timedelta(seconds=1)
    available_now, _ = is_bike_available_for_rentalos(db, bike.id, now, current_window_end)
    return "available" if available_now else "booked"


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
        firstname=customer.firstname,
        lastname=customer.lastname,
        current_flag_status=customer.current_flag_status,
        previous_booking_count=previous_booking_count,
        latest_flag=RentalCustomerFlagSummary.model_validate(latest_flag) if latest_flag else None,
        latest_note=_latest_customer_note(db, customer.id, customer.shop_id),
    )


@router.get("/me", response_model=RentalOSMeResponse)
def get_rentalos_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the current user's RentalOS owner/staff access."""
    owned_shops = db.query(Shop).filter(Shop.owner_id == current_user.id).all()
    owned_shop_ids = {shop.id for shop in owned_shops}
    active_staff_memberships = (
        db.query(RentalStaff)
        .options(joinedload(RentalStaff.shop))
        .filter(
            RentalStaff.user_id == current_user.id,
            RentalStaff.is_active == True,
        )
        .all()
    )

    owned_access = [
        RentalOSAccessShop(
            shop_id=shop.id,
            shop_name=shop.name,
            role="owner",
            staff_id=None,
            is_active=True,
        )
        for shop in owned_shops
    ]
    staff_access = [
        RentalOSAccessShop(
            shop_id=staff.shop_id,
            shop_name=staff.shop.name,
            role=staff.role,
            staff_id=staff.id,
            is_active=staff.is_active,
        )
        for staff in active_staff_memberships
        if staff.shop_id not in owned_shop_ids
    ]

    return RentalOSMeResponse(
        has_rentalos_access=bool(owned_access or staff_access),
        user_id=current_user.id,
        email=current_user.email,
        user_type=current_user.user_type,
        owned_shops=owned_access,
        staff_shops=staff_access,
    )


@router.post("/staff", response_model=RentalStaffResponse, status_code=status.HTTP_201_CREATED)
def create_rental_staff(
    staff_create: RentalStaffCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a staff user or attach an existing user to an owned shop."""
    shop = assert_rentalos_owner_access(db, staff_create.shop_id, current_user)
    role = _validate_staff_role(staff_create.role)
    email = str(staff_create.email).strip().lower()

    staff_user = (
        db.query(User)
        .filter(func.lower(func.trim(User.email)) == email)
        .first()
    )
    if staff_user:
        if staff_user.id == shop.owner_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Shop owner does not need a staff membership.",
            )
        existing_staff = (
            db.query(RentalStaff)
            .filter(
                RentalStaff.shop_id == shop.id,
                RentalStaff.user_id == staff_user.id,
            )
            .first()
        )
        if existing_staff:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This user is already staff for this shop.",
            )
    else:
        if not staff_create.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password is required for new staff user.",
            )
        if len(staff_create.password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long.",
            )
        staff_user = User(
            email=email,
            password=hash_password(staff_create.password),
            firstname=staff_create.firstname,
            lastname=staff_create.lastname,
            phone_number=staff_create.phone_number,
            user_type="shop_staff",
            is_email_verified=True,
        )
        db.add(staff_user)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email/user conflict.",
            )

    db_staff = RentalStaff(
        shop_id=shop.id,
        user_id=staff_user.id,
        role=role,
        is_active=True,
    )
    db.add(db_staff)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This user is already staff for this shop.",
        )

    db_staff = (
        db.query(RentalStaff)
        .options(joinedload(RentalStaff.user))
        .filter(RentalStaff.id == db_staff.id)
        .first()
    )
    return _staff_response(db_staff)


@router.get("/staff", response_model=list[RentalStaffResponse])
def list_rental_staff(
    shop_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List active and inactive staff for an owned shop."""
    assert_rentalos_owner_access(db, shop_id, current_user)
    staff_rows = (
        db.query(RentalStaff)
        .options(joinedload(RentalStaff.user))
        .filter(RentalStaff.shop_id == shop_id)
        .order_by(RentalStaff.created_at.desc())
        .all()
    )
    return [_staff_response(staff) for staff in staff_rows]


@router.patch("/staff/{staff_id}", response_model=RentalStaffResponse)
def update_rental_staff(
    staff_id: int,
    staff_update: RentalStaffUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update staff profile details or activate/deactivate a staff membership."""
    staff = (
        db.query(RentalStaff)
        .options(joinedload(RentalStaff.user))
        .filter(RentalStaff.id == staff_id)
        .first()
    )
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff not found.",
        )

    assert_rentalos_owner_access(db, staff.shop_id, current_user)

    if staff_update.role is not None:
        staff.role = _validate_staff_role(staff_update.role)
    if staff_update.firstname is not None:
        staff.user.firstname = staff_update.firstname
    if staff_update.lastname is not None:
        staff.user.lastname = staff_update.lastname
    if staff_update.phone_number is not None:
        staff.user.phone_number = staff_update.phone_number
    if staff_update.is_active is not None:
        staff.is_active = staff_update.is_active

    staff.updated_at = tz.now()
    staff.user.updated_at = tz.now()
    db.commit()
    db.refresh(staff)
    db.refresh(staff.user)
    return _staff_response(staff)


@router.get("/catalog/vehicles", response_model=list[CatalogVehicleResponse])
def get_catalog_vehicles(
    shop_id: int = Query(...),
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List RentalOS catalog vehicles for a shop."""
    assert_rentalos_shop_access(db, shop_id, current_user)
    if (start_time and not end_time) or (end_time and not start_time):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both start_time and end_time are required for availability checks.",
        )
    if start_time and end_time:
        start_time, end_time = _validate_time_range(start_time, end_time)

    bikes = (
        db.query(Bike)
        .options(joinedload(Bike.image))
        .filter(Bike.shop_id == shop_id)
        .all()
    )

    return [
        CatalogVehicleResponse(
            bike_id=bike.id,
            shop_id=bike.shop_id,
            name=bike.name,
            model=bike.model,
            bike_type=bike.bike_type,
            price_per_hour=bike.price_per_hour,
            price_per_day=bike.price_per_day,
            condition=bike.condition,
            maintenance_status=bike.maintenance_status,
            is_available=bike.is_available,
            image_url=_bike_image_url(bike),
            rentalos_availability_status=_availability_status(db, bike, start_time, end_time),
        )
        for bike in bikes
    ]


@router.get("/customers/search", response_model=RentalCustomerSearchResponse)
def search_customer_by_phone(
    shop_id: int = Query(...),
    phone: str = Query(..., min_length=3, max_length=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Find a RentalOS customer by exact phone number inside one shop."""
    assert_rentalos_shop_access(db, shop_id, current_user)
    customer = (
        db.query(RentalCustomer)
        .filter(
            RentalCustomer.shop_id == shop_id,
            RentalCustomer.phone_number == phone,
        )
        .first()
    )
    if not customer:
        return RentalCustomerSearchResponse(found=False, phone_number=phone)
    return _customer_search_response(db, customer, phone)


@router.post("/customers", response_model=RentalCustomerOut, status_code=status.HTTP_201_CREATED)
def create_rental_customer(
    customer: RentalCustomerCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a RentalOS customer scoped to one shop."""
    assert_rentalos_shop_access(db, customer.shop_id, current_user)
    existing = (
        db.query(RentalCustomer)
        .filter(
            RentalCustomer.shop_id == customer.shop_id,
            RentalCustomer.phone_number == customer.phone_number,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Customer already exists for this shop.",
        )

    now = tz.now()
    db_customer = RentalCustomer(
        shop_id=customer.shop_id,
        phone_number=customer.phone_number,
        firstname=customer.firstname,
        lastname=customer.lastname,
        document_consent=customer.document_consent,
        document_consent_at=now if customer.document_consent else None,
        marketing_consent=customer.marketing_consent,
        marketing_consent_at=now if customer.marketing_consent else None,
        created_by_user_id=current_user.id,
    )
    db.add(db_customer)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Customer already exists for this shop.",
        )
    db.refresh(db_customer)
    return db_customer


@router.post("/bookings", response_model=RentalBookingResponse, status_code=status.HTTP_201_CREATED)
def create_rental_booking(
    booking: RentalBookingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create an offline RentalOS booking without touching online payments/bookings."""
    _, staff = assert_rentalos_shop_access(db, booking.shop_id, current_user)
    start_time, end_time = _validate_time_range(booking.start_time, booking.end_time)

    bike, _inventory, availability = check_bike_availability_by_id(
        db,
        booking.bike_id,
        start_time,
        end_time,
        lock=True,
    )
    if not bike:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bike with ID {booking.bike_id} not found",
        )
    if bike.shop_id != booking.shop_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bike does not belong to this shop.",
        )

    if not availability.is_available:
        detail = availability.reason or "Vehicle is already booked for this time."
        if "fully booked" in detail.lower():
            detail = "Vehicle is already booked for this time."
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )

    customer = (
        db.query(RentalCustomer)
        .filter(
            RentalCustomer.shop_id == booking.shop_id,
            RentalCustomer.phone_number == booking.phone_number,
        )
        .first()
    )
    if not customer:
        customer = RentalCustomer(
            shop_id=booking.shop_id,
            phone_number=booking.phone_number,
            firstname=booking.firstname,
            lastname=booking.lastname,
            created_by_user_id=current_user.id,
        )
        db.add(customer)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            customer = (
                db.query(RentalCustomer)
                .filter(
                    RentalCustomer.shop_id == booking.shop_id,
                    RentalCustomer.phone_number == booking.phone_number,
                )
                .first()
            )
            if not customer:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Could not create or reuse customer for this booking.",
                )
    else:
        if booking.firstname and not customer.firstname:
            customer.firstname = booking.firstname
        if booking.lastname and not customer.lastname:
            customer.lastname = booking.lastname

    db_booking = RentalBooking(
        shop_id=booking.shop_id,
        customer_id=customer.id,
        bike_id=booking.bike_id,
        staff_id=staff.id if staff else None,
        start_time=start_time,
        end_time=end_time,
        status="confirmed",
        total_amount=booking.total_amount,
        advance_paid=booking.advance_paid,
        balance_due=booking.balance_due,
        security_deposit=booking.security_deposit,
    )
    db.add(db_booking)
    db.flush()

    if booking.notes:
        db.add(
            RentalBookingNote(
                booking_id=db_booking.id,
                note=booking.notes,
                created_by_user_id=current_user.id,
            )
        )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not create booking.",
        )

    db.refresh(db_booking)
    return (
        db.query(RentalBooking)
        .options(joinedload(RentalBooking.customer), joinedload(RentalBooking.bike))
        .filter(RentalBooking.id == db_booking.id)
        .first()
    )


@router.get("/bookings", response_model=list[RentalBookingResponse])
def list_rental_bookings(
    shop_id: int = Query(...),
    status_filter: str | None = Query(None, alias="status"),
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List RentalOS bookings scoped to one accessible shop."""
    assert_rentalos_shop_access(db, shop_id, current_user)
    query = (
        db.query(RentalBooking)
        .options(joinedload(RentalBooking.customer), joinedload(RentalBooking.bike))
        .filter(RentalBooking.shop_id == shop_id)
    )
    if status_filter:
        query = query.filter(RentalBooking.status == status_filter)
    if start_date:
        query = query.filter(RentalBooking.start_time >= tz.ensure_aware(start_date))
    if end_date:
        query = query.filter(RentalBooking.end_time <= tz.ensure_aware(end_date))
    if start_date and end_date and tz.ensure_aware(start_date) > tz.ensure_aware(end_date):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before end_date.",
        )

    return query.order_by(RentalBooking.start_time.desc()).all()


@router.get("/bookings/{booking_id}", response_model=RentalBookingResponse)
def get_rental_booking(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get one RentalOS booking if it belongs to an accessible shop."""
    booking = (
        db.query(RentalBooking)
        .options(joinedload(RentalBooking.customer), joinedload(RentalBooking.bike))
        .filter(RentalBooking.id == booking_id)
        .first()
    )
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rental booking with ID {booking_id} not found",
        )

    assert_rentalos_shop_access(db, booking.shop_id, current_user)
    return booking


@router.post(
    "/bookings/{booking_id}/documents",
    response_model=RentalBookingDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_rental_booking_document(
    booking_id: int,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload DL/ID proof for a RentalOS booking into private Azure Blob Storage."""
    booking = get_accessible_rental_booking(db, booking_id, current_user)
    if document_type not in DOCUMENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="document_type must be driving_license or id_proof.",
        )

    content = validate_rentalos_upload(file, DOCUMENT_CONTENT_TYPES, _max_rentalos_upload_bytes())
    blob_name = build_rentalos_blob_name(booking.shop_id, booking.id, "documents", file.content_type)
    upload = upload_rentalos_blob(blob_name, content, file.content_type)

    # TODO: Before production, serve sensitive RentalOS files through signed URL /
    # authenticated download flow instead of exposing direct blob URLs.
    db_document = RentalBookingDocument(
        booking_id=booking.id,
        document_type=document_type,
        file_url=upload.blob_url,
        file_name=file.filename,
        content_type=file.content_type,
        uploaded_by_user_id=current_user.id,
    )
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    return db_document


@router.get("/bookings/{booking_id}/documents", response_model=list[RentalBookingDocumentResponse])
def list_rental_booking_documents(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List uploaded DL/ID proof metadata for an accessible RentalOS booking."""
    booking = get_accessible_rental_booking(db, booking_id, current_user)
    return (
        db.query(RentalBookingDocument)
        .filter(RentalBookingDocument.booking_id == booking.id)
        .order_by(RentalBookingDocument.created_at.desc())
        .all()
    )


@router.post(
    "/bookings/{booking_id}/handover-photo",
    response_model=RentalHandoverPhotoResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_rental_handover_photo(
    booking_id: int,
    file: UploadFile = File(...),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    location_accuracy_meters: int | None = Form(None),
    location_address: str | None = Form(None),
    location_permission_granted: bool = Form(False),
    captured_at: datetime | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload customer-with-vehicle handover photo into private Azure Blob Storage."""
    booking = get_accessible_rental_booking(db, booking_id, current_user)
    if latitude is not None and not -90 <= latitude <= 90:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="latitude must be between -90 and 90.",
        )
    if longitude is not None and not -180 <= longitude <= 180:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="longitude must be between -180 and 180.",
        )

    content = validate_rentalos_upload(file, HANDOVER_PHOTO_CONTENT_TYPES, _max_rentalos_upload_bytes())
    blob_name = build_rentalos_blob_name(booking.shop_id, booking.id, "handover", file.content_type)
    upload = upload_rentalos_blob(blob_name, content, file.content_type)

    # TODO: Before production, serve sensitive RentalOS files through signed URL /
    # authenticated download flow instead of exposing direct blob URLs.
    db_photo = RentalHandoverPhoto(
        booking_id=booking.id,
        image_url=upload.blob_url,
        latitude=latitude,
        longitude=longitude,
        location_accuracy_meters=location_accuracy_meters,
        location_address=location_address,
        location_permission_granted=location_permission_granted,
        captured_at=captured_at,
        uploaded_by_user_id=current_user.id,
    )
    db.add(db_photo)
    db.commit()
    db.refresh(db_photo)
    return db_photo


@router.get("/bookings/{booking_id}/handover-photos", response_model=list[RentalHandoverPhotoResponse])
def list_rental_handover_photos(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List handover photo metadata for an accessible RentalOS booking."""
    booking = get_accessible_rental_booking(db, booking_id, current_user)
    return (
        db.query(RentalHandoverPhoto)
        .filter(RentalHandoverPhoto.booking_id == booking.id)
        .order_by(RentalHandoverPhoto.created_at.desc())
        .all()
    )


@router.post("/bookings/{booking_id}/payments", response_model=RentalPaymentResponse, status_code=status.HTTP_201_CREATED)
def record_rental_payment(
    booking_id: int,
    payment: RentalPaymentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Record an offline RentalOS payment without touching online Payment/Razorpay flows."""
    booking = get_accessible_rental_booking(db, booking_id, current_user)
    _validate_payment(payment)

    if booking.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot record payment for a cancelled booking.",
        )
    if booking.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot record payment for a completed booking.",
        )

    db_payment = RentalPayment(
        booking_id=booking.id,
        payment_type=payment.payment_type,
        amount=payment.amount,
        status=payment.status,
        method=payment.method,
        reference_number=payment.reference_number,
        paid_at=tz.ensure_aware(payment.paid_at) if payment.paid_at else None,
        received_by_user_id=current_user.id,
    )
    db.add(db_payment)
    _apply_payment_summary(booking, payment)
    db.commit()
    db.refresh(db_payment)
    return db_payment


@router.get("/bookings/{booking_id}/payments", response_model=list[RentalPaymentResponse])
def list_rental_payments(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List offline RentalOS payments for an accessible booking."""
    booking = get_accessible_rental_booking(db, booking_id, current_user)
    return (
        db.query(RentalPayment)
        .filter(RentalPayment.booking_id == booking.id)
        .order_by(RentalPayment.created_at.desc())
        .all()
    )


@router.post("/bookings/{booking_id}/complete", response_model=RentalBookingResponse)
def complete_rental_booking(
    booking_id: int,
    completion: RentalBookingCompleteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a RentalOS booking completed and optionally save completion note/flag."""
    booking = get_accessible_rental_booking(db, booking_id, current_user)
    if booking.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot complete a cancelled booking.",
        )
    if booking.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking is already completed.",
        )

    if completion.customer_flag_severity and not completion.customer_flag_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid customer flag type.",
        )
    if completion.customer_flag_note and not completion.customer_flag_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid customer flag type.",
        )

    note_text = completion.note.strip() if completion.note else None
    flag_note = completion.customer_flag_note.strip() if completion.customer_flag_note else None
    flag_type = None
    flag_severity = None
    if completion.customer_flag_type:
        candidate_note = flag_note or note_text
        flag_type, flag_severity = _validate_customer_flag(
            completion.customer_flag_type,
            completion.customer_flag_severity,
            candidate_note,
        )

    booking.status = "completed"
    booking.completed_at = tz.ensure_aware(completion.completed_at) if completion.completed_at else tz.now()

    if note_text:
        db.add(
            RentalBookingNote(
                booking_id=booking.id,
                note=note_text,
                created_by_user_id=current_user.id,
            )
        )

    if flag_type:
        customer = db.query(RentalCustomer).filter(RentalCustomer.id == booking.customer_id).first()
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rental customer not found.",
            )
        safe_flag_note = flag_note or note_text or f"Customer marked as {flag_type} at trip completion."
        _create_customer_flag(
            db=db,
            customer=customer,
            flag_type=flag_type,
            severity=flag_severity,
            note=safe_flag_note,
            is_active=True,
            current_user=current_user,
        )

    db.commit()
    return (
        db.query(RentalBooking)
        .options(joinedload(RentalBooking.customer), joinedload(RentalBooking.bike))
        .filter(RentalBooking.id == booking.id)
        .first()
    )


@router.post("/bookings/{booking_id}/notes", response_model=RentalBookingNoteResponse, status_code=status.HTTP_201_CREATED)
def create_rental_booking_note(
    booking_id: int,
    note_create: RentalBookingNoteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add an operational note to an accessible RentalOS booking."""
    booking = get_accessible_rental_booking(db, booking_id, current_user)
    note = _require_non_empty_note(note_create.note)
    db_note = RentalBookingNote(
        booking_id=booking.id,
        note=note,
        created_by_user_id=current_user.id,
    )
    db.add(db_note)
    db.commit()
    db.refresh(db_note)
    return db_note


@router.get("/bookings/{booking_id}/notes", response_model=list[RentalBookingNoteResponse])
def list_rental_booking_notes(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List notes for an accessible RentalOS booking."""
    booking = get_accessible_rental_booking(db, booking_id, current_user)
    return (
        db.query(RentalBookingNote)
        .filter(RentalBookingNote.booking_id == booking.id)
        .order_by(RentalBookingNote.created_at.desc())
        .all()
    )


@router.post("/customers/{customer_id}/flags", response_model=RentalCustomerFlagResponse, status_code=status.HTTP_201_CREATED)
def create_rental_customer_flag(
    customer_id: int,
    flag_create: RentalCustomerFlagCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a shop-scoped RentalOS customer flag."""
    customer = get_accessible_rental_customer(db, customer_id, current_user)
    note = _require_non_empty_note(flag_create.note, "A note is required for this customer flag.")
    flag_type, severity = _validate_customer_flag(flag_create.flag_type, flag_create.severity, note)
    db_flag = _create_customer_flag(
        db=db,
        customer=customer,
        flag_type=flag_type,
        severity=severity,
        note=note,
        is_active=flag_create.is_active,
        current_user=current_user,
    )
    db.commit()
    db.refresh(db_flag)
    return db_flag


@router.get("/customers/{customer_id}/flags", response_model=list[RentalCustomerFlagResponse])
def list_rental_customer_flags(
    customer_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List shop-scoped flags for an accessible RentalOS customer."""
    customer = get_accessible_rental_customer(db, customer_id, current_user)
    return (
        db.query(RentalCustomerFlag)
        .filter(
            RentalCustomerFlag.customer_id == customer.id,
            RentalCustomerFlag.shop_id == customer.shop_id,
        )
        .order_by(RentalCustomerFlag.created_at.desc())
        .all()
    )
