import base64
import hashlib
import hmac
import json
import os
import urllib.error
import urllib.request
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.v1.oauth2 import get_current_user
from app.db.database import get_db
from app.db.models import BikeInventory, Booking, Payment, User
from app.schemas.payments import PaymentOrderCreate, PaymentOrderOut, PaymentOut, PaymentVerify, RefundCreate
from app.utils import tz

router = APIRouter(prefix="/payments", tags=["payments"])

RAZORPAY_API_BASE = "https://api.razorpay.com/v1"


def _razorpay_keys() -> tuple[str, str]:
    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")
    if not key_id or not key_secret:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Razorpay keys not configured")
    return key_id, key_secret


def _razorpay_request(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    key_id, key_secret = _razorpay_keys()
    auth_bytes = f"{key_id}:{key_secret}".encode("utf-8")
    auth_header = base64.b64encode(auth_bytes).decode("utf-8")
    data = json.dumps(payload or {}).encode("utf-8") if payload is not None else None

    request = urllib.request.Request(
        f"{RAZORPAY_API_BASE}{path}",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth_header}",
        },
        method=method,
    )

    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Razorpay error: {error_body}")
    except urllib.error.URLError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Razorpay connection error: {exc.reason}")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Razorpay request failed: {str(exc)}")


def _booking_amount_paise(booking: Booking) -> int:
    if booking.total_price is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Booking total price is not set")
    if booking.total_price <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Booking total price must be greater than zero")
    return int(booking.total_price * 100)


def _verify_payment_signature(order_id: str, payment_id: str, signature: str) -> None:
    _, key_secret = _razorpay_keys()
    signature_payload = f"{order_id}|{payment_id}".encode("utf-8")
    expected_signature = hmac.new(key_secret.encode("utf-8"), signature_payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_signature, signature):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Razorpay signature")


def _verify_webhook_signature(body: bytes, signature: str | None) -> None:
    webhook_secret = os.getenv("RAZORPAY_WEBHOOK_SECRET")
    if not webhook_secret:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Razorpay webhook secret not configured")
    if not signature:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing Razorpay webhook signature")

    expected_signature = hmac.new(webhook_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_signature, signature):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Razorpay webhook signature")


@router.post("/", response_model=PaymentOrderOut, status_code=status.HTTP_201_CREATED)
def create_payment(payment: PaymentOrderCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create or reuse a Razorpay order for a confirmed booking."""
    if current_user.user_type != "customer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only customers can create payments")

    booking = db.query(Booking).filter(Booking.id == payment.booking_id, Booking.customer_id == current_user.id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found or does not belong to you")
    if booking.status not in {"confirmed", "paid"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only confirmed bookings can be paid")

    key_id, _ = _razorpay_keys()
    amount_paise = _booking_amount_paise(booking)

    existing_payment = (
        db.query(Payment)
        .filter(Payment.booking_id == booking.id, Payment.status.in_(["created", "paid"]))
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
        "amount": amount_paise,
        "currency": "INR",
        "receipt": f"booking_{booking.id}",
        "notes": {
            "booking_id": str(booking.id),
            "customer_id": str(current_user.id),
        },
    }
    order_data = _razorpay_request("POST", "/orders", order_payload)
    order_id = order_data.get("id")
    if not order_id:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Razorpay order creation failed")

    db_payment = Payment(
        order_id=order_id,
        payment_id=None,
        booking_id=booking.id,
        amount=amount_paise,
        refunded_amount=0,
        currency="INR",
        razorpay_signature=None,
        status="created",
    )
    db.add(db_payment)
    db.commit()
    return PaymentOrderOut(order_id=order_id, amount=amount_paise, currency="INR", key_id=key_id)


@router.post("/verify", status_code=status.HTTP_200_OK)
def verify_payment(payload: PaymentVerify, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Verify Razorpay Checkout response and mark the booking as paid."""
    if current_user.user_type != "customer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only customers can verify payments")

    db_payment = db.query(Payment).filter(Payment.order_id == payload.order_id).first()
    if not db_payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

    booking = db.query(Booking).filter(Booking.id == db_payment.booking_id, Booking.customer_id == current_user.id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only verify payments for your own bookings")

    if db_payment.status == "paid":
        return {"message": "Payment already verified"}

    _verify_payment_signature(payload.order_id, payload.payment_id, payload.razorpay_signature)

    db_payment.payment_id = payload.payment_id
    db_payment.razorpay_signature = payload.razorpay_signature
    db_payment.status = "paid"
    db_payment.updated_at = tz.now()
    booking.status = "paid"
    booking.updated_at = tz.now()
    db.commit()
    db.refresh(db_payment)
    return {"message": "Payment verified successfully"}


@router.put("/cancel/{order_id}", status_code=status.HTTP_200_OK)
def cancel_payment(order_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Cancel an unpaid local payment order. Paid payments must use refund."""
    if current_user.user_type != "customer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only customers can cancel payments")

    db_payment = db.query(Payment).filter(Payment.order_id == order_id).first()
    if not db_payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

    booking = db.query(Booking).filter(Booking.id == db_payment.booking_id, Booking.customer_id == current_user.id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only cancel payments for your own bookings")
    if db_payment.status == "paid":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Paid payments must be refunded")

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

    booking = db.query(Booking).filter(Booking.id == db_payment.booking_id, Booking.customer_id == current_user.id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only view payments for your own bookings")
    return db_payment


@router.get("/booking/{booking_id}", response_model=PaymentOut)
def get_payment_for_booking(booking_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.id == booking_id, Booking.customer_id == current_user.id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found or does not belong to you")

    db_payment = (
        db.query(Payment)
        .filter(Payment.booking_id == booking.id)
        .order_by(Payment.created_at.desc())
        .first()
    )
    if not db_payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return db_payment


@router.post("/refund", response_model=PaymentOut, status_code=status.HTTP_200_OK)
def refund_payment(payload: RefundCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a Razorpay refund for a paid booking."""
    if current_user.user_type != "customer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only customers can request refunds")

    db_payment = db.query(Payment).filter(Payment.order_id == payload.order_id).first()
    if not db_payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

    booking = db.query(Booking).filter(Booking.id == db_payment.booking_id, Booking.customer_id == current_user.id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only request refunds for your own bookings")
    if db_payment.status not in {"paid", "refund_pending"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only paid payments can be refunded")
    if not db_payment.payment_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment ID is missing")

    refundable_amount = db_payment.amount - (db_payment.refunded_amount or 0)
    refund_amount = payload.amount if payload.amount is not None else refundable_amount
    if refund_amount <= 0 or refund_amount > refundable_amount:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid refund amount")

    refund_data = _razorpay_request(
        "POST",
        f"/payments/{db_payment.payment_id}/refund",
        {
            "amount": refund_amount,
            "notes": {
                "booking_id": str(booking.id),
                "reason": payload.reason or "customer_requested",
            },
        },
    )

    db_payment.refund_id = refund_data.get("id")
    db_payment.refunded_amount = (db_payment.refunded_amount or 0) + refund_amount
    db_payment.status = "refunded" if db_payment.refunded_amount >= db_payment.amount else "refund_pending"
    db_payment.updated_at = tz.now()
    booking.status = "refunded" if db_payment.status == "refunded" else "refund_pending"
    booking.updated_at = tz.now()
    db.commit()
    db.refresh(db_payment)
    return db_payment


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """Receive Razorpay payment/refund events.

    Configure RAZORPAY_WEBHOOK_SECRET in production. The frontend verification
    path gives fast feedback; this endpoint is the server-side source of truth.
    """
    body = await request.body()
    _verify_webhook_signature(body, x_razorpay_signature)
    event = json.loads(body.decode("utf-8"))
    event_name = event.get("event")

    if event_name == "payment.captured":
        payment_entity = event.get("payload", {}).get("payment", {}).get("entity", {})
        order_id = payment_entity.get("order_id")
        payment_id = payment_entity.get("id")
        if order_id and payment_id:
            db_payment = db.query(Payment).filter(Payment.order_id == order_id).first()
            if db_payment:
                booking = db.query(Booking).filter(Booking.id == db_payment.booking_id).first()
                db_payment.payment_id = payment_id
                db_payment.status = "paid"
                db_payment.updated_at = tz.now()
                if booking and booking.status in {"confirmed", "pending"}:
                    booking.status = "paid"
                    booking.updated_at = tz.now()
                db.commit()

    if event_name in {"refund.processed", "refund.created"}:
        refund_entity = event.get("payload", {}).get("refund", {}).get("entity", {})
        payment_id = refund_entity.get("payment_id")
        refund_id = refund_entity.get("id")
        refund_amount = int(refund_entity.get("amount") or 0)
        if payment_id and refund_id:
            db_payment = db.query(Payment).filter(Payment.payment_id == payment_id).first()
            if db_payment:
                booking = db.query(Booking).filter(Booking.id == db_payment.booking_id).first()
                db_payment.refund_id = refund_id
                db_payment.refunded_amount = max(db_payment.refunded_amount or 0, refund_amount)
                db_payment.status = "refunded" if db_payment.refunded_amount >= db_payment.amount else "refund_pending"
                db_payment.updated_at = tz.now()
                if booking:
                    if booking.status not in {"cancelled", "rejected"}:
                        booking.status = "refunded" if db_payment.status == "refunded" else "refund_pending"
                        booking.updated_at = tz.now()
                db.commit()

    return {"status": "ok"}
