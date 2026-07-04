# RentalOS Frontend Handoff

This document describes only the RentalOS backend currently implemented in:

- `app/api/v1/rentalos.py`
- `app/schemas/rentalos.py`

No frontend, separate staff login, analytics, invoices, signed download flow, or dynamic RBAC exists yet.

## Base API Prefix

RentalOS endpoints are under:

```text
/api/v1/rentalos
```

Normal login is the existing app login endpoint:

```text
/api/v1/login
```

## Authentication

All RentalOS endpoints require the existing bearer JWT:

```http
Authorization: Bearer <access_token>
```

Frontend must not build a separate RentalOS staff login. Owners and staff both authenticate through:

```http
POST /api/v1/login
Content-Type: application/x-www-form-urlencoded
```

Request:

```text
username=staff@example.com&password=strongpassword123
```

Response:

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer"
}
```

The token works for RentalOS through the existing `get_current_user` dependency.

## Exact Flow After Login

1. User submits normal login form to `POST /api/v1/login`.
2. Store returned `access_token`.
3. Immediately call `GET /api/v1/rentalos/me`.
4. If `has_rentalos_access=false`, do not show RentalOS.
5. If `owned_shops` has entries, show owner RentalOS dashboard.
6. If only `staff_shops` has entries, show limited staff RentalOS dashboard.
7. Let users with multiple shops choose an active shop from `owned_shops` or `staff_shops`.
8. Use the selected `shop_id` for shop-scoped counter APIs.

## RentalOS Access Discovery

### Get Current RentalOS Access

```http
GET /api/v1/rentalos/me
```

Authenticated normal user. This endpoint tells the frontend whether to show:

- owner RentalOS dashboard
- limited staff RentalOS dashboard
- no RentalOS access

Staff response:

```json
{
  "has_rentalos_access": true,
  "user_id": 12,
  "email": "staff@example.com",
  "user_type": "shop_staff",
  "owned_shops": [],
  "staff_shops": [
    {
      "shop_id": 3,
      "shop_name": "ABC Rentals",
      "role": "staff",
      "staff_id": 9,
      "is_active": true
    }
  ]
}
```

Owner response:

```json
{
  "has_rentalos_access": true,
  "user_id": 5,
  "email": "owner@example.com",
  "user_type": "shop_owner",
  "owned_shops": [
    {
      "shop_id": 1,
      "shop_name": "Owner Shop",
      "role": "owner",
      "staff_id": null,
      "is_active": true
    }
  ],
  "staff_shops": []
}
```

No-access response:

```json
{
  "has_rentalos_access": false,
  "user_id": 8,
  "email": "customer@example.com",
  "user_type": "customer",
  "owned_shops": [],
  "staff_shops": []
}
```

Inactive staff memberships are not returned in `staff_shops`.

## Owner Vs Staff Dashboard Behavior

### Owner

Owner access is not stored as `RentalStaff`. It is derived from:

```text
Shop.owner_id == current_user.id
```

Owner can:

- access all RentalOS counter APIs for owned shops
- create staff
- list staff
- update staff details
- activate/deactivate staff

### Staff

Staff is a normal `User` with an active `RentalStaff` membership.

Staff can use the counter workflow only:

- catalog
- customer phone lookup
- customer create
- booking create/list/detail
- document upload/list
- handover photo upload/list
- payment record/list
- trip completion
- booking notes create/list
- customer flags create/list

Staff cannot use:

- staff management APIs
- shop settings
- analytics
- reports
- marketplace dashboard metrics
- online payment/Razorpay APIs
- marketplace owner-only actions
- global/admin data

Inactive staff can still log in if credentials are valid, but `/rentalos/me` will not list inactive memberships and counter APIs will return 403.

## Staff Management Endpoints

Staff management is owner-only. Do not show staff management UI to staff users.

### Create Staff

```http
POST /api/v1/rentalos/staff
Content-Type: application/json
```

Required fields:

- `shop_id`
- `email`
- `firstname`
- `lastname`
- `phone_number`

Required only when creating a new user:

- `password`

Optional:

- `role`, default `"staff"`

Only `"staff"` is valid. Do not send `owner`, `admin`, `manager`, or custom roles.

Request:

```json
{
  "shop_id": 1,
  "email": "counter@example.com",
  "password": "strongpassword123",
  "firstname": "Counter",
  "lastname": "Staff",
  "phone_number": "9999999999",
  "role": "staff"
}
```

Response:

```json
{
  "id": 9,
  "shop_id": 1,
  "user_id": 12,
  "email": "counter@example.com",
  "firstname": "Counter",
  "lastname": "Staff",
  "phone_number": "9999999999",
  "role": "staff",
  "is_active": true,
  "created_at": "2026-07-01T09:00:00",
  "updated_at": "2026-07-01T09:00:00"
}
```

Backend behavior:

- If email does not exist, backend creates a normal `User` with `user_type="shop_staff"` and `is_email_verified=true`.
- If email exists, backend does not change password or existing user type.
- Duplicate staff membership returns 409.
- Shop owner cannot be added as staff for their own shop.
- Password/password hash is never returned.

### List Staff

```http
GET /api/v1/rentalos/staff?shop_id=1
```

Owner-only. Returns active and inactive staff for the owned shop.

Response:

```json
[
  {
    "id": 9,
    "shop_id": 1,
    "user_id": 12,
    "email": "counter@example.com",
    "firstname": "Counter",
    "lastname": "Staff",
    "phone_number": "9999999999",
    "role": "staff",
    "is_active": true,
    "created_at": "2026-07-01T09:00:00",
    "updated_at": "2026-07-01T09:00:00"
  }
]
```

### Update Or Deactivate Staff

```http
PATCH /api/v1/rentalos/staff/{staff_id}
Content-Type: application/json
```

Optional fields:

- `email` (used for booking and final invoice emails)
- `firstname`
- `lastname`
- `phone_number`
- `is_active`
- `role`

Only `"staff"` is valid for `role`.

Request:

```json
{
  "firstname": "Updated",
  "phone_number": "8888888888",
  "is_active": false,
  "role": "staff"
}
```

Response: updated staff response object.

There is no hard-delete staff endpoint in the MVP. Use `is_active=false`.

## Implemented Endpoint List

### Auth

```http
POST /api/v1/login
```

Existing normal login for customers, owners, and staff.

### Access And Staff

```http
GET /api/v1/rentalos/me
POST /api/v1/rentalos/staff
GET /api/v1/rentalos/staff?shop_id=1
PATCH /api/v1/rentalos/staff/{staff_id}
```

### Catalog

```http
GET /api/v1/rentalos/catalog/vehicles?shop_id=1
GET /api/v1/rentalos/catalog/vehicles?shop_id=1&start_time=2026-07-01T10:00:00Z&end_time=2026-07-01T18:00:00Z
```

Required query:

- `shop_id`

Optional query:

- `start_time`
- `end_time`

If one time is provided, both are required.

Response:

```json
[
  {
    "bike_id": 12,
    "shop_id": 1,
    "name": "Activa",
    "model": "6G",
    "bike_type": "scooty",
    "price_per_hour": 100,
    "price_per_day": 500,
    "condition": "good",
    "maintenance_status": "available",
    "is_available": true,
    "image_url": "https://...",
    "rentalos_availability_status": "available"
  }
]
```

`rentalos_availability_status` values:

- `available`
- `booked`
- `maintenance`
- `unavailable`

### Customer Search

```http
GET /api/v1/rentalos/customers/search?shop_id=1&phone=9999999999
```

Found response:

```json
{
  "found": true,
  "phone_number": "9999999999",
  "id": 7,
  "firstname": "Asha",
  "lastname": "Rao",
  "current_flag_status": "good_customer",
  "previous_booking_count": 3,
  "latest_flag": {
    "id": 2,
    "flag_type": "good_customer",
    "severity": "info",
    "note": "Returned on time",
    "created_at": "2026-07-01T12:00:00"
  },
  "latest_note": "Returned on time"
}
```

Not found response:

```json
{
  "found": false,
  "phone_number": "9999999999",
  "id": null,
  "firstname": null,
  "lastname": null,
  "current_flag_status": null,
  "previous_booking_count": 0,
  "latest_flag": null,
  "latest_note": null
}
```

### Create Customer

```http
POST /api/v1/rentalos/customers
Content-Type: application/json
```

Required fields:

- `shop_id`
- `phone_number`

Optional fields:

- `email`
- `firstname`
- `lastname`
- `document_consent`
- `marketing_consent`

Request:

```json
{
  "shop_id": 1,
  "phone_number": "9999999999",
  "email": "asha@example.com",
  "firstname": "Asha",
  "lastname": "Rao",
  "document_consent": true,
  "marketing_consent": false
}
```

### Create Booking

```http
POST /api/v1/rentalos/bookings
Content-Type: application/json
```

Required fields:

- `shop_id`
- `bike_id`
- `phone_number`
- `start_time`
- `end_time`

Optional fields:

- `firstname`
- `lastname`
- `total_amount`
- `advance_paid`
- `balance_due`
- `security_deposit`
- `notes`

Request:

```json
{
  "shop_id": 1,
  "bike_id": 12,
  "phone_number": "9999999999",
  "email": "asha@example.com",
  "firstname": "Asha",
  "lastname": "Rao",
  "start_time": "2026-07-01T10:00:00Z",
  "end_time": "2026-07-01T18:00:00Z",
  "total_amount": 1000,
  "advance_paid": 200,
  "balance_due": 800,
  "security_deposit": 500,
  "notes": "Walk-in booking"
}
```

Response:

```json
{
  "id": 21,
  "shop_id": 1,
  "customer_id": 7,
  "bike_id": 12,
  "start_time": "2026-07-01T10:00:00",
  "end_time": "2026-07-01T18:00:00",
  "status": "confirmed",
  "total_amount": 1000,
  "advance_paid": 200,
  "balance_due": 800,
  "security_deposit": 500,
  "created_at": "2026-07-01T09:30:00",
  "customer": {
    "id": 7,
    "phone_number": "9999999999",
    "email": "asha@example.com",
    "firstname": "Asha",
    "lastname": "Rao",
    "current_flag_status": null
  },
  "bike": {
    "id": 12,
    "name": "Activa",
    "model": "6G",
    "bike_type": "scooty"
  }
}
```

Booking conflict checks use both existing online `Booking` rows and RentalOS `RentalBooking` rows. Online `pending`, `paid`, and `confirmed` bookings block RentalOS availability. RentalOS `draft`, `confirmed`, and `active` bookings block availability.

### Booking Read APIs

```http
GET /api/v1/rentalos/bookings?shop_id=1
GET /api/v1/rentalos/bookings?shop_id=1&status=confirmed
GET /api/v1/rentalos/bookings?shop_id=1&start_date=2026-07-01T00:00:00Z&end_date=2026-07-31T23:59:59Z
GET /api/v1/rentalos/bookings/{booking_id}
```

List response: array of booking response objects.

Detail response: one booking response object.

## File Uploads

RentalOS document and handover uploads use `multipart/form-data`. Backend stores files as private Cloudflare R2 objects and returns short-lived signed `file_url` / `image_url` values.

Do not cache signed file URLs long-term. Refetch the booking documents or handover photos list before opening a file if the page may have been idle.

### Upload Booking Document

```http
POST /api/v1/rentalos/bookings/{booking_id}/documents
Content-Type: multipart/form-data
```

Required form fields:

- `document_type`: `driving_license` or `id_proof`
- `file`

Allowed file types:

- `image/jpeg`
- `image/png`
- `image/webp`
- `application/pdf`

The backend checks both the declared MIME type and the file signature.

Example:

```bash
curl -X POST "$API_BASE/api/v1/rentalos/bookings/21/documents" \
  -H "Authorization: Bearer $TOKEN" \
  -F "document_type=driving_license" \
  -F "file=@/path/to/license.jpg;type=image/jpeg"
```

Response:

```json
{
  "id": 3,
  "booking_id": 21,
  "document_type": "driving_license",
  "file_url": "https://...",
  "file_name": "license.jpg",
  "content_type": "image/jpeg",
  "created_at": "2026-07-01T09:35:00"
}
```

### List Booking Documents

```http
GET /api/v1/rentalos/bookings/{booking_id}/documents
```

### Upload Handover Photo

```http
POST /api/v1/rentalos/bookings/{booking_id}/handover-photo
Content-Type: multipart/form-data
```

Required form fields:

- `file`

Optional form fields:

- `latitude`
- `longitude`
- `location_accuracy_meters`
- `location_address`
- `location_permission_granted`
- `captured_at`

Allowed file types:

- `image/jpeg`
- `image/png`
- `image/webp`

PDF is not allowed for handover photos.

Latitude must be between `-90` and `90`. Longitude must be between `-180` and `180`.

Example:

```bash
curl -X POST "$API_BASE/api/v1/rentalos/bookings/21/handover-photo" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/handover.jpg;type=image/jpeg" \
  -F "location_permission_granted=true" \
  -F "latitude=12.9716" \
  -F "longitude=77.5946" \
  -F "location_accuracy_meters=20" \
  -F "location_address=Bengaluru"
```

### List Handover Photos

```http
GET /api/v1/rentalos/bookings/{booking_id}/handover-photos
```

## Payments

### Record Payment

```http
POST /api/v1/rentalos/bookings/{booking_id}/payments
Content-Type: application/json
```

Required fields:

- `payment_type`
- `amount`

Optional fields:

- `status`, default `paid`
- `method`
- `reference_number`
- `paid_at`

Allowed `payment_type`:

- `advance`
- `balance`
- `security_deposit`
- `refund`
- `extra_charge`

Allowed `status`:

- `pending`
- `partial`
- `paid`
- `refunded`

Allowed `method`:

- `cash`
- `upi`
- `card`
- `bank_transfer`
- `other`

Request:

```json
{
  "payment_type": "advance",
  "amount": 200,
  "status": "paid",
  "method": "upi",
  "reference_number": "UPI123",
  "paid_at": "2026-07-01T09:45:00Z"
}
```

Backend summary updates:

- Paid `advance` increases booking `advance_paid`.
- Paid `balance` reduces booking `balance_due`, not below `0`.
- Paid `security_deposit` increases booking `security_deposit`.
- `refund` with status `paid` or `refunded` reduces `security_deposit`, not below `0`.
- Paid `extra_charge` increases `total_amount` only if `total_amount` already exists.

Cancelled and completed bookings reject payment recording.

### List Payments

```http
GET /api/v1/rentalos/bookings/{booking_id}/payments
```

## Trip Completion

### Complete Booking

```http
POST /api/v1/rentalos/bookings/{booking_id}/complete
Content-Type: application/json
```

Optional fields:

- `completed_at`
- `note`
- `customer_flag_type`
- `customer_flag_severity`
- `customer_flag_note`

Allowed `customer_flag_type`:

- `good_customer`
- `normal_customer`
- `late_return`
- `payment_issue`
- `damage_issue`
- `document_issue`
- `watchlist`
- `blocked`

Allowed `customer_flag_severity`:

- `info`
- `warning`
- `blocked`

Negative/risky flag types require a note:

- `late_return`
- `payment_issue`
- `damage_issue`
- `document_issue`
- `watchlist`
- `blocked`

Request:

```json
{
  "completed_at": "2026-07-01T18:15:00Z",
  "note": "Returned on time",
  "customer_flag_type": "good_customer",
  "customer_flag_severity": "info",
  "customer_flag_note": "Clean return"
}
```

Response: updated booking response object.

Cancelled bookings cannot be completed. Already completed bookings cannot be completed again.

## Booking Notes

```http
POST /api/v1/rentalos/bookings/{booking_id}/notes
GET /api/v1/rentalos/bookings/{booking_id}/notes
```

Create note request:

```json
{
  "note": "Customer returned helmet separately."
}
```

## Customer Flags

```http
POST /api/v1/rentalos/customers/{customer_id}/flags
GET /api/v1/rentalos/customers/{customer_id}/flags
```

Create flag required fields:

- `flag_type`
- `note`

Optional fields:

- `severity`
- `is_active`, default `true`

Request:

```json
{
  "flag_type": "watchlist",
  "severity": "warning",
  "note": "Late return and delayed balance payment.",
  "is_active": true
}
```

If `is_active` is true, backend updates `RentalCustomer.current_flag_status` to the new flag type.

## Common Errors

Auth/access:

```json
{"detail": "Could not validate credentials"}
```

```json
{"detail": "You do not have access to this shop."}
```

```json
{"detail": "Only shop owners can manage staff."}
```

Staff management:

```json
{"detail": "Invalid staff role."}
```

```json
{"detail": "Password is required for new staff user."}
```

```json
{"detail": "This user is already staff for this shop."}
```

```json
{"detail": "Shop owner does not need a staff membership."}
```

Missing records:

```json
{"detail": "Rental booking not found."}
```

```json
{"detail": "Rental customer not found."}
```

Booking/catalog:

```json
{"detail": "Both start_time and end_time are required for availability checks."}
```

```json
{"detail": "Booking start time must be before end time."}
```

```json
{"detail": "Vehicle is already booked for this time."}
```

Uploads:

```json
{"detail": "Unsupported file type: application/pdf"}
```

```json
{"detail": "File size exceeds the 5MB limit."}
```

```json
{"detail": "latitude must be between -90 and 90."}
```

Payments:

```json
{"detail": "Invalid payment type."}
```

```json
{"detail": "Cannot record payment for a completed booking."}
```

Completion/flags:

```json
{"detail": "Cannot complete a cancelled booking."}
```

```json
{"detail": "Booking is already completed."}
```

```json
{"detail": "Invalid customer flag type."}
```

```json
{"detail": "A note is required for this customer flag."}
```

## Frontend Routing Recommendations

Suggested routes:

- `/login`: existing normal login.
- `/rentalos`: access gate that calls `GET /api/v1/rentalos/me`.
- `/rentalos/no-access`: no RentalOS access message.
- `/rentalos/owner/:shopId`: owner RentalOS dashboard.
- `/rentalos/staff/:shopId`: limited staff counter dashboard.
- `/rentalos/owner/:shopId/staff`: owner-only staff management.
- `/rentalos/:shopId/catalog`: counter catalog.
- `/rentalos/:shopId/bookings`: booking list.
- `/rentalos/bookings/:bookingId`: booking detail/capture/payment/completion workflow.

Routing rules:

- Never route to owner staff management unless selected shop is in `owned_shops`.
- Route staff to limited counter dashboard using `staff_shops`.
- If user owns and staffs different shops, let them choose shop/context.
- If a selected shop disappears from `/rentalos/me`, clear active shop and reroute through the access gate.

## Recommended Counter Flow Order

1. Login through `/api/v1/login`.
2. Call `/api/v1/rentalos/me`.
3. Select active shop from `owned_shops` or `staff_shops`.
4. Load catalog with `GET /catalog/vehicles?shop_id=...`.
5. Search customer by phone.
6. If not found, create customer or let booking creation create/reuse by phone.
7. Select vehicle and time range; optionally reload catalog with `start_time` and `end_time`.
8. Create booking.
9. Upload DL/ID document.
10. Upload handover photo.
11. Record advance/security deposit/balance payments as needed.
12. Add notes as needed.
13. Complete booking, optionally adding final note and customer flag.
14. On future phone lookup, show `current_flag_status`, latest flag, latest note, and previous booking count.

## What Frontend Should Not Build Yet

Do not build UI for:

- separate RentalOS staff login
- dynamic RBAC or custom permission editor
- staff invitation email flow
- hard-delete staff
- analytics
- reports
- invoices
- SMS/email/WhatsApp automation
- Razorpay or online payment settlement inside RentalOS
- signed file download/access management
- OCR or DL/Aadhaar number extraction
- customer export
- global customer blacklist
- native app flows
- complex ledger/accounting

Do not mix RentalOS offline flows with existing online marketplace booking/payment flows.
