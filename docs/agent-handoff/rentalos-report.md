# RentalOS Report

RentalOS files:

- API router: `app/api/v1/rentalos.py`
- Schemas: `app/schemas/rentalos.py`
- Models: `app/db/models.py`
- Azure utility: `app/utils/rentalos_azure_blob.py`
- Migration: `alembic/versions/7c3a91d4e8f2_add_rentalos_database_foundation.py`

## Product summary

RentalOS is an offline shop counter system for walk-in rentals. It is separate from the existing GoPanda online marketplace dashboard. Shop staff or owners can show a catalog, look up or create customers by phone, create offline bookings, capture document/handover proof, record offline payments, complete trips, add notes, and flag customers.

Important separation:

- `RentalBooking` is separate from online `Booking`.
- `RentalPayment` is separate from Razorpay `Payment`.
- RentalOS document/handover uploads use Azure Blob Storage.
- Existing marketplace bike/shop image uploads use Cloudinary and should remain untouched.

## Backend architecture

Router:

- `router = APIRouter(prefix="/rentalos", tags=["rentalos"])`
- Mounted in `app/main.py` with `/api/v1`.
- Final base API prefix: `/api/v1/rentalos`.

Access helpers:

- `get_user_rental_staff_membership`
- `get_rentalos_shop_access`
- `assert_rentalos_shop_access`
- `assert_rentalos_owner_access`
- `get_accessible_rental_booking`
- `get_accessible_rental_customer`

Availability/conflict helpers:

- `_validate_time_range`
- `validate_rentalos_bike_status`
- `has_rentalos_booking_conflict`
- `is_bike_available_for_rentalos`
- `_availability_status`

Upload helpers:

- `_max_rentalos_upload_bytes`
- `validate_rentalos_upload`
- `build_rentalos_blob_name`
- `upload_rentalos_blob`

Payment/flag helpers:

- `_validate_payment`
- `_apply_payment_summary`
- `_validate_customer_flag`
- `_infer_customer_flag_severity`
- `_create_customer_flag`
- `_validate_staff_role`
- `_staff_response`

## RentalOS models

Defined in `app/db/models.py`:

- `RentalStaff`: active shop staff membership.
- `RentalCustomer`: shop-scoped offline customer, unique on `(shop_id, phone_number)`, consent fields, current flag status.
- `RentalCustomerFlag`: shop/customer-scoped customer flag history.
- `RentalBooking`: offline booking with payment summary fields and status.
- `RentalBookingDocument`: DL/ID document metadata.
- `RentalHandoverPhoto`: handover image metadata with optional location.
- `RentalPayment`: offline payment ledger.
- `RentalBookingNote`: booking/customer operational notes.

## RentalOS schemas

Defined in `app/schemas/rentalos.py`:

- `RentalCustomerFlagSummary`
- `RentalCustomerSearchResponse`
- `RentalStaffCreate`
- `RentalStaffUpdate`
- `RentalStaffResponse`
- `RentalOSAccessShop`
- `RentalOSMeResponse`
- `RentalCustomerCreate`
- `RentalCustomerOut`
- `RentalBookingCreate`
- `RentalBookingCustomerSummary`
- `RentalBookingBikeSummary`
- `RentalBookingResponse`
- `CatalogVehicleResponse`
- `RentalBookingDocumentResponse`
- `RentalHandoverPhotoResponse`
- `RentalPaymentCreate`
- `RentalPaymentResponse`
- `RentalBookingPaymentSummary`
- `RentalBookingCompleteRequest`
- `RentalBookingNoteCreate`
- `RentalBookingNoteResponse`
- `RentalCustomerFlagCreate`
- `RentalCustomerFlagResponse`

## RentalOS endpoints

- `GET /api/v1/rentalos/me`
- `POST /api/v1/rentalos/staff`
- `GET /api/v1/rentalos/staff`
- `PATCH /api/v1/rentalos/staff/{staff_id}`
- `GET /api/v1/rentalos/catalog/vehicles`
- `GET /api/v1/rentalos/customers/search`
- `POST /api/v1/rentalos/customers`
- `POST /api/v1/rentalos/bookings`
- `GET /api/v1/rentalos/bookings`
- `GET /api/v1/rentalos/bookings/{booking_id}`
- `POST /api/v1/rentalos/bookings/{booking_id}/documents`
- `GET /api/v1/rentalos/bookings/{booking_id}/documents`
- `POST /api/v1/rentalos/bookings/{booking_id}/handover-photo`
- `GET /api/v1/rentalos/bookings/{booking_id}/handover-photos`
- `POST /api/v1/rentalos/bookings/{booking_id}/payments`
- `GET /api/v1/rentalos/bookings/{booking_id}/payments`
- `POST /api/v1/rentalos/bookings/{booking_id}/complete`
- `POST /api/v1/rentalos/bookings/{booking_id}/notes`
- `GET /api/v1/rentalos/bookings/{booking_id}/notes`
- `POST /api/v1/rentalos/customers/{customer_id}/flags`
- `GET /api/v1/rentalos/customers/{customer_id}/flags`

No frontend endpoints, analytics, invoices, SMS/email automation, OCR, or native app APIs were observed for RentalOS.

## Access control

All RentalOS endpoints require `get_current_user`.

Allowed:

- Shop owner where `Shop.owner_id == current_user.id`.
- Active staff where `RentalStaff.user_id == current_user.id`, `RentalStaff.shop_id == shop_id`, and `RentalStaff.is_active == True`.

Rejected:

- Users with no shop ownership and no active staff membership.
- Inactive staff.
- Staff assigned to a different shop.

Booking-scoped endpoints derive access from `RentalBooking.shop_id`. Customer flag endpoints derive access from `RentalCustomer.shop_id`.

Owner-only staff management:

- Owner is not stored as `RentalStaff`.
- Owner access is derived from `Shop.owner_id == current_user.id`.
- `assert_rentalos_owner_access` is used for staff management APIs.
- Staff cannot create/list/update staff.
- Staff creation may create a normal `User` with `user_type="shop_staff"` and `is_email_verified=True`.
- Public signup remains restricted to `customer` and `shop_owner`.

Current user access discovery:

- `GET /api/v1/rentalos/me` returns `owned_shops`, active `staff_shops`, and `has_rentalos_access`.
- Inactive staff memberships are not listed in `staff_shops`.

## Customer phone lookup flow

Endpoint/function:

- `GET /api/v1/rentalos/customers/search`
- `search_customer_by_phone`

Inputs:

- `shop_id`
- `phone`

Flow:

1. Check owner/staff access for `shop_id`.
2. Query `RentalCustomer` by exact `shop_id` and `phone_number`.
3. If not found, return `RentalCustomerSearchResponse(found=False, phone_number=phone)`.
4. If found, return customer fields, `current_flag_status`, previous booking count, latest active flag, and latest note.

Important behavior:

- Phone lookup is shop-scoped.
- Same phone can exist in another shop.

## Catalog availability flow

Endpoint/function:

- `GET /api/v1/rentalos/catalog/vehicles`
- `get_catalog_vehicles`

Inputs:

- `shop_id`
- optional `start_time` and `end_time`; both required together.

Flow:

1. Check owner/staff access for `shop_id`.
2. Validate time range if supplied.
3. Load bikes for the shop with images.
4. For each bike, compute `rentalos_availability_status`.

Availability statuses:

- `unavailable`: `Bike.is_available` is false.
- `maintenance`: `Bike.maintenance_status` is one of `maintenance`, `repair`, `cleaning`.
- `booked`: time window conflicts.
- `available`: no blocking status/conflict.

## Offline booking create flow

Endpoint/function:

- `POST /api/v1/rentalos/bookings`
- `create_rental_booking`

Inputs:

- `shop_id`
- `bike_id`
- `phone_number`
- optional `firstname`, `lastname`
- `start_time`
- `end_time`
- optional `total_amount`
- `advance_paid`
- `balance_due`
- `security_deposit`
- optional `notes`

Flow:

1. Check owner/staff access for `shop_id`.
2. Validate `start_time < end_time`.
3. Load and lock `Bike` by `bike_id` using `with_for_update()`.
4. Verify bike exists and belongs to `shop_id`.
5. Validate bike status with `validate_rentalos_bike_status`.
6. Check online/offline booking conflicts with `has_rentalos_booking_conflict`.
7. Reuse existing `RentalCustomer` by `(shop_id, phone_number)` or create one.
8. Create `RentalBooking` with status `confirmed`.
9. Set `staff_id` only when access came through active `RentalStaff`; owners get `staff_id=None`.
10. Add optional `RentalBookingNote`.
11. Commit and return booking with customer and bike summary.

Important behavior:

- This flow does not create online `Booking`.
- This flow does not touch Razorpay `Payment`.
- This flow does not mutate `BikeInventory` counters.

## Conflict check logic

Constants in `app/api/v1/rentalos.py`:

- `ONLINE_CONFLICT_STATUSES = ["pending", "paid", "confirmed"]`
- `RENTALOS_CONFLICT_STATUSES = ["draft", "confirmed", "active"]`

Overlap filter:

- `model.start_time < end_time`
- `model.end_time > start_time`

Conflict rules:

- Online pending `Booking` blocks RentalOS booking.
- Online confirmed `Booking` blocks RentalOS booking.
- Online paid `Booking` blocks RentalOS booking.
- Online completed/cancelled bookings should not block RentalOS booking.
- RentalOS draft/confirmed/active bookings block.
- RentalOS completed/cancelled bookings should not block.
- Back-to-back bookings should not conflict because equality at boundaries does not match the overlap filter.

Code note:

- `has_rentalos_booking_conflict` contains a TODO that existing online booking creation should later use the same shared bike lock and availability service before creating `Booking` rows.

Audit concern:

- Online `Booking` creation still uses its own conflict logic. RentalOS includes online `pending`, `paid`, and `confirmed` in its conflict set, but a future shared availability service should keep both flows consistent.

## Azure document upload flow

Endpoint/function:

- `POST /api/v1/rentalos/bookings/{booking_id}/documents`
- `upload_rental_booking_document`

Multipart fields:

- `file` required.
- `document_type` required.

Allowed document types:

- `driving_license`
- `id_proof`

Allowed content types:

- `image/jpeg`
- `image/png`
- `image/webp`
- `application/pdf`

Flow:

1. Load booking by `booking_id`.
2. Authorize through `booking.shop_id`.
3. Validate `document_type`.
4. Validate content type, size, and non-empty body with `validate_rentalos_upload`.
5. Build blob name using `build_rentalos_blob_name(booking.shop_id, booking.id, "documents", file.content_type)`.
6. Upload to Azure with `upload_rentalos_blob`.
7. Store metadata in `RentalBookingDocument`.

Blob pattern:

```text
rentalos/shops/{shop_id}/bookings/{booking_id}/documents/{uuid}.{ext}
```

Security note:

- Original filename is kept only in `file_name`.
- Original filename is not trusted for blob path.
- Sensitive docs need signed/authenticated download flow later.
- Code TODO says: "Before production, serve sensitive RentalOS files through signed URL / authenticated download flow instead of exposing direct blob URLs."

## Handover photo and location metadata flow

Endpoint/function:

- `POST /api/v1/rentalos/bookings/{booking_id}/handover-photo`
- `upload_rental_handover_photo`

Multipart fields:

- `file` required.
- `latitude` optional float.
- `longitude` optional float.
- `location_accuracy_meters` optional int.
- `location_address` optional string.
- `location_permission_granted` optional bool, default false.
- `captured_at` optional datetime.

Allowed content types:

- `image/jpeg`
- `image/png`
- `image/webp`

PDFs are rejected for handover photos.

Validation:

- Latitude must be between `-90` and `90`.
- Longitude must be between `-180` and `180`.
- Location is optional.
- If `location_permission_granted` is false, lat/lng are not required.

Blob pattern:

```text
rentalos/shops/{shop_id}/bookings/{booking_id}/handover/{uuid}.{ext}
```

## Payment recording flow

Endpoint/functions:

- `POST /api/v1/rentalos/bookings/{booking_id}/payments`
- `GET /api/v1/rentalos/bookings/{booking_id}/payments`
- `record_rental_payment`
- `_validate_payment`
- `_apply_payment_summary`

Allowed payment types:

- `advance`
- `balance`
- `security_deposit`
- `refund`
- `extra_charge`

Allowed statuses:

- `pending`
- `partial`
- `paid`
- `refunded`

Allowed methods:

- `cash`
- `upi`
- `card`
- `bank_transfer`
- `other`

Behavior:

- Rejects non-positive amount.
- Rejects payment recording for cancelled booking.
- Rejects payment recording for completed booking.
- Creates `RentalPayment`.
- Updates `RentalBooking` summary fields:
  - paid advance increases `advance_paid`
  - paid balance decreases `balance_due`, not below 0
  - paid security deposit increases `security_deposit`
  - paid/refunded refund decreases `security_deposit`, not below 0
  - paid extra charge increases `total_amount` only if `total_amount` is not `None`

Important separation:

- This flow does not call Razorpay.
- This flow does not create or mutate marketplace `Payment`.

## Trip completion flow

Endpoint/function:

- `POST /api/v1/rentalos/bookings/{booking_id}/complete`
- `complete_rental_booking`

Inputs:

- optional `completed_at`
- optional `note`
- optional `customer_flag_type`
- optional `customer_flag_severity`
- optional `customer_flag_note`

Behavior:

- Rejects cancelled booking.
- Rejects already completed booking.
- Marks booking `status = "completed"`.
- Sets `completed_at` to provided aware datetime or current time.
- Adds optional `RentalBookingNote`.
- Adds optional active `RentalCustomerFlag`.
- Active flag updates `RentalCustomer.current_flag_status`.

Important behavior:

- Completed `RentalBooking` should not block future availability because `completed` is not in `RENTALOS_CONFLICT_STATUSES`.

## Notes and customer flags flow

Notes:

- `POST /api/v1/rentalos/bookings/{booking_id}/notes`
- `GET /api/v1/rentalos/bookings/{booking_id}/notes`
- Empty notes are rejected.
- Notes are booking-scoped and access-controlled through `RentalBooking.shop_id`.

Flags:

- `POST /api/v1/rentalos/customers/{customer_id}/flags`
- `GET /api/v1/rentalos/customers/{customer_id}/flags`
- Flags are customer/shop-scoped and access-controlled through `RentalCustomer.shop_id`.

Allowed flag types:

- `good_customer`
- `normal_customer`
- `late_return`
- `payment_issue`
- `damage_issue`
- `document_issue`
- `watchlist`
- `blocked`

Allowed severities:

- `info`
- `warning`
- `blocked`

Negative flag types require a note:

- `late_return`
- `payment_issue`
- `damage_issue`
- `document_issue`
- `watchlist`
- `blocked`

## What RentalOS deliberately does not implement yet

Not observed in current backend:

- Frontend.
- Staff management endpoints.
- Signed URL or authenticated download endpoint for sensitive files.
- OCR or DL/Aadhaar number extraction.
- Sensitive number storage.
- Razorpay payment integration.
- Analytics.
- Invoices.
- SMS/email automation.
- Campaigns.
- AI.
- Native app.
- Complex RBAC.
- Complex settlement.

## Security concerns

- Sensitive document and handover metadata currently returns blob URLs. Signed/authenticated download or equivalent protection is not implemented yet.
- Azure RentalOS container privacy is not in place yet.
- File validation relies on upload content type and size; no content sniffing or malware scanning observed.
- No model-level enum/check constraints for status/type fields.
- RentalOS staff management is minimal: owner can create/list/update/deactivate staff, but there is no invitation email, hard delete, custom password reset, or dynamic RBAC.
- Customer flags and notes may contain sensitive operational data; access tests should be strict.

## Audit concerns

- Verify all RentalOS endpoints use owner/staff access and cannot be bypassed with body `shop_id`.
- Verify `RentalBooking` never mutates online `Booking` or `Payment`.
- Verify `RentalPayment` never mutates Razorpay `Payment`.
- Verify marketplace Cloudinary uploads remain unchanged.
- Verify back-to-back bookings succeed.
- Verify completed/cancelled RentalOS bookings do not block future bookings.
- Verify online paid bookings block RentalOS availability.
- Verify staff management remains owner-only and inactive staff cannot access counter APIs.
- Verify rate-limiter isolation in tests.

## Test plan

High-priority tests:

1. Owner/staff access matrix for every RentalOS route family.
2. Customer phone lookup found/not found and latest flag/note.
3. Unique `(shop_id, phone_number)` behavior.
4. Catalog availability for available/unavailable/maintenance/booked vehicles.
5. RentalOS booking create conflicts against online pending/paid/confirmed bookings.
6. RentalOS booking create conflicts against RentalOS draft/confirmed/active bookings.
7. Completed/cancelled online and RentalOS bookings do not block availability.
8. Back-to-back booking succeeds.
9. Document upload validates document type, content type, size, and access.
10. Handover photo upload rejects PDF and invalid lat/lng.
11. Payment recording updates summary fields exactly.
12. Cancelled/completed RentalOS bookings reject new payment.
13. Completion creates optional note/flag and stops blocking availability.
14. Marketplace regression: online booking and Razorpay payment still use `Booking` and `Payment`; Cloudinary uploads still use existing utility.
