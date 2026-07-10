from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.v1.oauth2 import get_current_user
from app.db.database import get_db
from app.db.models import RentalPayment, User
from app.schemas.rentalos import RentalPaymentCreate, RentalPaymentResponse
from .utils import (
    get_accessible_rental_booking,
    tz,
    _validate_payment,
    _apply_payment_summary,
)


router = APIRouter()

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

