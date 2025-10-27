from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, Literal


class BookingCreate(BaseModel):
    bike_id: int
    start_time: datetime
    end_time: datetime
    # Note: customer_id is automatically set from the authenticated user


class Booking(BookingCreate):
    id: int
    customer_id: int
    status: Literal["pending", "confirmed", "completed", "cancelled"]
    total_price: Optional[int] = None  # Price in cents, calculated from bike hourly/daily rate
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BookingUpdate(BaseModel):
    status: Optional[Literal["pending", "confirmed", "completed", "cancelled"]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class BookingOut(Booking):
    pass
