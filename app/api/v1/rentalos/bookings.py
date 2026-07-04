from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile, status, Response
from sqlalchemy.orm import Session
from app.api.v1.oauth2 import get_current_user
from app.db.database import get_db
from app.db.models import *
from app.schemas.rentalos import *
from .utils import *

router = APIRouter()

@router.post("/bookings", response_model=RentalBookingResponse, status_code=status.HTTP_201_CREATED)
def create_rental_booking(
    booking: RentalBookingCreate,
    background_tasks: BackgroundTasks,
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
            email=_normalize_optional_email(str(booking.email) if booking.email else None),
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
        if booking.email:
            customer.email = _normalize_optional_email(str(booking.email))
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
    created_booking = (
        db.query(RentalBooking)
        .options(
            joinedload(RentalBooking.customer),
            joinedload(RentalBooking.bike),
            joinedload(RentalBooking.shop),
        )
        .filter(RentalBooking.id == db_booking.id)
        .first()
    )
    enqueue_rentalos_invoice_email(background_tasks, created_booking, [], "booking_created")
    return created_booking


@router.get("/bookings", response_model=list[RentalBookingResponse])
def list_rental_bookings(
    shop_id: int = Query(...),
    status_filter: str | None = Query(None, alias="status"),
    customer_id: int | None = None,
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
    if customer_id is not None:
        customer = (
            db.query(RentalCustomer.id)
            .filter(
                RentalCustomer.id == customer_id,
                RentalCustomer.shop_id == shop_id,
            )
            .first()
        )
        if not customer:
            return []
        query = query.filter(RentalBooking.customer_id == customer_id)
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


@router.post("/bookings/{booking_id}/cancel", response_model=RentalBookingResponse)
def cancel_rental_booking(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel a RentalOS booking and free the vehicle for that time window."""
    booking = get_accessible_rental_booking(db, booking_id, current_user)
    if booking.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel a completed booking.",
        )
    if booking.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking is already cancelled.",
        )

    booking.status = "cancelled"
    db.commit()
    return (
        db.query(RentalBooking)
        .options(joinedload(RentalBooking.customer), joinedload(RentalBooking.bike))
        .filter(RentalBooking.id == booking.id)
        .first()
    )


@router.post("/bookings/{booking_id}/complete", response_model=RentalBookingResponse)
def complete_rental_booking(
    booking_id: int,
    completion: RentalBookingCompleteRequest,
    background_tasks: BackgroundTasks,
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
    completed_booking = (
        db.query(RentalBooking)
        .options(
            joinedload(RentalBooking.customer),
            joinedload(RentalBooking.bike),
            joinedload(RentalBooking.shop),
        )
        .filter(RentalBooking.id == booking.id)
        .first()
    )
    payments = (
        db.query(RentalPayment)
        .filter(RentalPayment.booking_id == booking.id)
        .order_by(RentalPayment.created_at.asc())
        .all()
    )
    enqueue_rentalos_invoice_email(background_tasks, completed_booking, payments, "final")
    return completed_booking


