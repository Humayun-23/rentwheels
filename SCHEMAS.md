# Backend Schema Reference

This document summarizes the Pydantic schemas defined in the backend.

## Users

**File:** app/schemas/users.py

### UserCreate
- email: EmailStr
- password: string
- firstname: string (1-50)
- lastname: string (1-50)
- phone_number: string (10-20)
- user_type: "customer" | "shop_owner"

### User
- All fields from UserCreate
- id: int
- created_at: datetime
- updated_at: datetime

### UserLogin
- email: EmailStr
- password: string

### UserUpdate
- firstname: string (1-50), optional
- lastname: string (1-50), optional
- phone_number: string (10-20), optional

### UserOut
- email: EmailStr
- firstname: string
- lastname: string
- phone_number: string
- user_type: "customer" | "shop_owner"
- id: int
- created_at: datetime
- updated_at: datetime

## Admin

**File:** app/schemas/admin.py

### AdminCreate
- admin_user_id: int
- email: string
- password: string

### AdminRead
- admin_user_id: int
- email: string
- created_at: datetime

### AdminUpdate
- email: string, optional
- password: string, optional

### AdminOut
- All fields from AdminRead

## Bikes

**File:** app/schemas/bikes.py

### BikeCreate
- shop_id: int
- name: string
- model: string
- bike_type: "scooty" | "bike" | "car" | "mountain" | "road" | "hybrid" | "electric"
- engine_cc: int, optional
- description: string, optional
- price_per_hour: int
- price_per_day: int
- condition: "excellent" | "good" | "fair" (default: "good")
- is_available: bool (default: true)

### Bike
- All fields from BikeCreate
- id: int
- created_at: datetime
- updated_at: datetime

### BikeUpdate
- name: string, optional
- model: string, optional
- bike_type: same as BikeCreate, optional
- engine_cc: int, optional
- description: string, optional
- price_per_hour: int, optional
- price_per_day: int, optional
- condition: "excellent" | "good" | "fair", optional
- is_available: bool, optional

### BikeOut
- All fields from Bike

## Booking

**File:** app/schemas/booking.py

### BookingCreate
- bike_id: int
- start_time: datetime
- end_time: datetime

### Booking
- All fields from BookingCreate
- id: int
- customer_id: int
- status: "pending" | "confirmed" | "completed" | "cancelled"
- total_price: int, optional
- created_at: datetime
- updated_at: datetime

### BookingUpdate
- status: "pending" | "confirmed" | "completed" | "cancelled", optional
- start_time: datetime, optional
- end_time: datetime, optional

### BookingOut
- All fields from Booking

## Inventory

**File:** app/schemas/inventory.py

### BikeInventoryCreate
- bike_id: int
- shop_id: int
- total_quantity: int

### BikeInventoryUpdate
- total_quantity: int

### BikeInventory
- All fields from BikeInventoryCreate
- id: int
- available_quantity: int
- rented_quantity: int
- created_at: datetime
- updated_at: datetime

### BikeInventoryOut
- All fields from BikeInventory
- availability_percentage: float (computed)

### InventoryAvailability
- bike_id: int
- is_available: bool
- available_count: int
- total_count: int

## Password Reset

**File:** app/schemas/password_reset.py

### PasswordResetRequest
- email: EmailStr

### PasswordResetConfirm
- token: string (min length 1)
- new_password: string (8-128)

### PasswordResetResponse
- message: string

## Reviews

**File:** app/schemas/reviews.py

### ReviewBase
- rating: int (1-5)
- comment: string (max 500), optional

### ReviewCreate
- All fields from ReviewBase
- comment is sanitized before validation

### ReviewUpdate
- rating: int (1-5), optional
- comment: string (max 500), optional
- comment is sanitized before validation

### ReviewOut
- All fields from ReviewBase
- id: int
- customer_id: int
- shop_id: int
- created_at: datetime
- updated_at: datetime

## Shops

**File:** app/schemas/shops.py

### ShopCreate
- name: string
- description: string, optional
- phone_number: string (10-20)
- address: string
- city: string
- state: string, optional
- zip_code: string, optional
- opening_time: time, optional
- closing_time: time, optional
- is_active: bool (default: true)

### Shop
- All fields from ShopCreate
- id: int
- created_at: datetime
- updated_at: datetime

### ShopUpdate
- All fields from ShopCreate, optional

### ShopOut
- All fields from Shop

## Tokens

**File:** app/schemas/token.py

### Token
- access_token: string
- token_type: string

### TokenData
- user_id: int
