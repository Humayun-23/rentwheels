import base64
import hashlib
import hmac
import json
import os
import urllib.error
import urllib.request

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.v1.oauth2 import get_current_user
from app.db.database import get_db
from app.db.models import User, Booking, Payment
from app.schemas.payments import PaymentOrderCreate, PaymentOrderOut, PaymentOut, PaymentUpdate, PaymentVerify
from app.utils import tz

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/", response_model=PaymentOrderOut, status_code=status.HTTP_201_CREATED)
def create_payment(payment: PaymentOrderCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.user_type != "customer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only customers can create payments")
    # Verify that the booking exists and belongs to the current user
    booking = db.query(Booking).filter(Booking.id == payment.booking_id, Booking.customer_id == current_user.id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found or does not belong to you")
    if booking.total_price is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Booking total price is not set")

    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")
    if not key_id or not key_secret:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Razorpay keys not configured")

    existing_payment = (
        db.query(Payment)
        .filter(Payment.booking_id == booking.id, Payment.status == "created")
        .order_by(Payment.created_at.desc())
        .first()
    )
    if existing_payment:
        return PaymentOrderOut(
            order_id=existing_payment.order_id,
            amount=existing_payment.amount,
            currency=existing_payment.currency,
            key_id=key_id,
        )

    order_payload = {
        "amount": booking.total_price,
        "currency": "INR",
        "receipt": f"booking_{booking.id}",
        "payment_capture": 1,
    }
    auth_bytes = f"{key_id}:{key_secret}".encode("utf-8")
    auth_header = base64.b64encode(auth_bytes).decode("utf-8")
    request = urllib.request.Request(
        "https://api.razorpay.com/v1/orders",
        data=json.dumps(order_payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth_header}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request) as response:
            order_data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Razorpay error: {error_body}")
    except urllib.error.URLError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Razorpay connection error: {exc.reason}")

    order_id = order_data.get("id")
    if not order_id:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Razorpay order creation failed")

    db_payment = Payment(
        order_id=order_id,
        payment_id=None,
        booking_id=booking.id,
        amount=booking.total_price,
        currency="INR",
        razorpay_signature=None,
        status="created",
    )
    db.add(db_payment)
    db.commit()
    return PaymentOrderOut(order_id=order_id, amount=booking.total_price, currency="INR", key_id=key_id)

@router.post("/verify", status_code=status.HTTP_200_OK)
def verify_payment(payload: PaymentVerify, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.user_type != "customer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only customers can verify payments")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")
    if not key_secret:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Razorpay keys not configured")

    db_payment = db.query(Payment).filter(Payment.order_id == payload.order_id).first()
    if not db_payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    # Verify that the payment belongs to a booking of the current user
    booking = db.query(Booking).filter(Booking.id == db_payment.booking_id, Booking.customer_id == current_user.id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only verify payments for your own bookings")
    if db_payment.status == "paid":
        return {"message": "Payment already verified"}

    signature_payload = f"{payload.order_id}|{payload.payment_id}".encode("utf-8")
    expected_signature = hmac.new(key_secret.encode("utf-8"), signature_payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_signature, payload.razorpay_signature):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Razorpay signature")

    db_payment.payment_id = payload.payment_id
    db_payment.razorpay_signature = payload.razorpay_signature
    db_payment.status = "paid"
    db_payment.updated_at = tz.now()
    db.commit()
    db.refresh(db_payment)
    return {"message": "Payment verified successfully"}

@router.put("/cancel/{order_id}", status_code=status.HTTP_200_OK)
def cancel_payment(order_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.user_type != "customer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only customers can cancel payments")
    db_payment = db.query(Payment).filter(Payment.order_id == order_id).first()
    if not db_payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    # Verify that the payment belongs to a booking of the current user
    booking=db.query(Booking).filter(Booking.id == db_payment.booking_id, Booking.customer_id == current_user.id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only cancel payments for your own bookings")
    db_payment.status = "cancelled"
    db_payment.updated_at = tz.now()
    db.commit()
    db.refresh(db_payment)
    return {"message": "Payment cancelled successfully"}

@router.get("/{order_id}", response_model=PaymentOut)
def get_payment(order_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_payment = db.query(Payment).filter(Payment.order_id == order_id).first()
    if not db_payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    # Verify that the payment belongs to a booking of the current user
    booking=db.query(Booking).filter(Booking.id == db_payment.booking_id, Booking.customer_id == current_user.id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only view payments for your own bookings")
    return db_payment

@router.post("/refund/{order_id}", status_code=status.HTTP_200_OK)
def refund_payment(order_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.user_type != "customer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only customers can request refunds")
    db_payment = db.query(Payment).filter(Payment.order_id == order_id).first()
    if not db_payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    # Verify that the payment belongs to a booking of the current user
    booking=db.query(Booking).filter(Booking.id == db_payment.booking_id, Booking.customer_id == current_user.id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only request refunds for your own bookings")
    if db_payment.status != "paid":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only paid payments can be refunded")
    db_payment.status = "refund_requested"
    db_payment.updated_at = tz.now()
    db.commit()
    db.refresh(db_payment)
    return {"message": "Refund requested successfully"}