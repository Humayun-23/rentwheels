from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class PaymentOrderCreate(BaseModel):
    booking_id: int


class PaymentOrderOut(BaseModel):
    order_id: str
    amount: int
    currency: str
    key_id: str


class PaymentVerify(BaseModel):
    order_id: str
    payment_id: str
    razorpay_signature: str


class PaymentUpdate(BaseModel):
    status: str
    updated_at: Optional[datetime] = None


class PaymentOut(BaseModel):
    order_id: str
    payment_id: Optional[str] = None
    booking_id: int
    amount: int
    currency: str
    razorpay_signature: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)