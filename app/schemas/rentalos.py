from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RentalCustomerFlagSummary(BaseModel):
    id: int
    flag_type: str
    severity: str
    note: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RentalCustomerSearchResponse(BaseModel):
    found: bool
    phone_number: str
    id: Optional[int] = None
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    current_flag_status: Optional[str] = None
    previous_booking_count: int = 0
    latest_flag: Optional[RentalCustomerFlagSummary] = None
    latest_note: Optional[str] = None


class RentalStaffCreate(BaseModel):
    shop_id: int
    email: EmailStr
    password: Optional[str] = None
    firstname: str = Field(..., min_length=1, max_length=50)
    lastname: str = Field(..., min_length=1, max_length=50)
    phone_number: str = Field(..., min_length=10, max_length=20)
    role: str = "staff"


class RentalStaffUpdate(BaseModel):
    firstname: Optional[str] = Field(None, min_length=1, max_length=50)
    lastname: Optional[str] = Field(None, min_length=1, max_length=50)
    phone_number: Optional[str] = Field(None, min_length=10, max_length=20)
    is_active: Optional[bool] = None
    role: Optional[str] = None


class RentalStaffResponse(BaseModel):
    id: int
    shop_id: int
    user_id: int
    email: str
    firstname: str
    lastname: str
    phone_number: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class RentalOSAccessShop(BaseModel):
    shop_id: int
    shop_name: str
    role: str
    staff_id: Optional[int] = None
    is_active: bool = True


class RentalOSMeResponse(BaseModel):
    has_rentalos_access: bool
    user_id: int
    email: str
    user_type: str
    owned_shops: list[RentalOSAccessShop]
    staff_shops: list[RentalOSAccessShop]


class RentalCustomerCreate(BaseModel):
    shop_id: int
    phone_number: str = Field(..., min_length=3, max_length=20)
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    document_consent: bool = False
    marketing_consent: bool = False


class RentalCustomerOut(BaseModel):
    id: int
    shop_id: int
    phone_number: str
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    current_flag_status: Optional[str] = None
    document_consent: bool = False
    marketing_consent: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RentalBookingCreate(BaseModel):
    shop_id: int
    bike_id: int
    phone_number: str = Field(..., min_length=3, max_length=20)
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    start_time: datetime
    end_time: datetime
    total_amount: Optional[int] = None
    advance_paid: int = 0
    balance_due: int = 0
    security_deposit: int = 0
    notes: Optional[str] = None


class RentalBookingCustomerSummary(BaseModel):
    id: int
    phone_number: str
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    current_flag_status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class RentalBookingBikeSummary(BaseModel):
    id: int
    name: str
    model: str
    bike_type: str

    model_config = ConfigDict(from_attributes=True)


class RentalBookingResponse(BaseModel):
    id: int
    shop_id: int
    customer_id: int
    bike_id: int
    start_time: datetime
    end_time: datetime
    status: str
    total_amount: Optional[int] = None
    advance_paid: int
    balance_due: int
    security_deposit: int
    created_at: datetime
    customer: Optional[RentalBookingCustomerSummary] = None
    bike: Optional[RentalBookingBikeSummary] = None

    model_config = ConfigDict(from_attributes=True)


class CatalogVehicleResponse(BaseModel):
    bike_id: int
    shop_id: int
    name: str
    model: str
    bike_type: str
    price_per_hour: int
    price_per_day: int
    condition: str
    maintenance_status: Optional[str] = None
    is_available: bool
    image_url: Optional[str] = None
    rentalos_availability_status: Literal["available", "booked", "maintenance", "unavailable"]


class RentalBookingDocumentResponse(BaseModel):
    id: int
    booking_id: int
    document_type: str
    file_url: str
    file_name: Optional[str] = None
    content_type: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RentalHandoverPhotoResponse(BaseModel):
    id: int
    booking_id: int
    image_url: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_accuracy_meters: Optional[int] = None
    location_address: Optional[str] = None
    location_permission_granted: bool = False
    captured_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RentalPaymentCreate(BaseModel):
    payment_type: str
    amount: int
    status: str = "paid"
    method: Optional[str] = None
    reference_number: Optional[str] = None
    paid_at: Optional[datetime] = None


class RentalPaymentResponse(BaseModel):
    id: int
    booking_id: int
    payment_type: str
    amount: int
    status: str
    method: Optional[str] = None
    reference_number: Optional[str] = None
    paid_at: Optional[datetime] = None
    received_by_user_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RentalBookingPaymentSummary(BaseModel):
    booking_id: int
    total_amount: Optional[int] = None
    advance_paid: int
    balance_due: int
    security_deposit: int


class RentalBookingCompleteRequest(BaseModel):
    completed_at: Optional[datetime] = None
    note: Optional[str] = None
    customer_flag_type: Optional[str] = None
    customer_flag_severity: Optional[str] = None
    customer_flag_note: Optional[str] = None


class RentalBookingNoteCreate(BaseModel):
    note: str


class RentalBookingNoteResponse(BaseModel):
    id: int
    booking_id: int
    note: str
    created_by_user_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RentalCustomerFlagCreate(BaseModel):
    flag_type: str
    severity: Optional[str] = None
    note: str
    is_active: bool = True


class RentalCustomerFlagResponse(BaseModel):
    id: int
    shop_id: int
    customer_id: int
    flag_type: str
    severity: str
    note: str
    is_active: bool
    created_by_user_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
