# Testing Targets Report

This report is for a Gemini backend audit/test-writing pass. It is based on code inspection, owner clarification, and a fresh local test run.

## Current test status

Existing test files:

- `tests/conftest.py`
- `tests/test_auth.py`
- `tests/test_booking.py`
- `tests/test_main.py`
- `tests/test_rentos_access.py`
- `tests/test_rentos_booking_conflicts.py`
- `tests/test_rentos_payments.py`
- `tests/test_rentos_staff_management.py`
- `tests/test_rentos_uploads.py`
- `tests/test_shops.py`
- `tests/test_users.py`

Existing test pattern:

- FastAPI `TestClient`.
- In-memory SQLite database: `SQLALCHEMY_DATABASE_URL = "sqlite://"`.
- `StaticPool`.
- `Base.metadata.create_all(bind=engine)` once per test session.
- Function-scoped transaction rollback.
- `app.dependency_overrides[get_db] = override_get_db`.

Fresh test result:

- `.venv/bin/pytest` collected 36 tests.
- Result: `36 passed`.

SlowAPI limiter behavior:

- The limiter can affect tests that call `/api/v1/login` repeatedly.
- Future auth-dependent tests should prefer direct `create_access_token({"user_id": user.id, "role": "user"})` helpers unless specifically testing login.
- If login behavior is under test, reset/isolate the limiter or configure test mode to avoid cross-test 429s.

## Suggested pytest/SQLite pattern

Follow the existing fixture style in `tests/conftest.py`. For RentalOS tests, create direct DB fixtures for:

- Verified owner `User(user_type="shop_owner", is_email_verified=True)`.
- Verified customer `User(user_type="customer", is_email_verified=True)`.
- Staff `User`, plus `RentalStaff`.
- Multiple shops with different owners.
- Bikes with `BikeInventory`.
- Online `Booking` rows.
- `RentalCustomer` rows.
- `RentalBooking` rows.

For auth:

- Prefer direct `create_access_token({"user_id": user.id, "role": "user"})` helper in tests to avoid login rate-limit noise, unless the test specifically targets login.
- If using login, reset limiter state or isolate rate limiter per test.

## High-priority unit tests

- `app/api/v1/rentalos.py::validate_rentalos_bike_status`
  - available bike passes
  - `is_available=False` fails
  - `maintenance_status in {"maintenance", "repair", "cleaning"}` fails
- `app/api/v1/rentalos.py::has_rentalos_booking_conflict`
  - online pending blocks
  - online confirmed blocks
  - online paid blocks, per product decision
  - online completed does not block
  - RentalOS draft/confirmed/active blocks
  - RentalOS completed/cancelled does not block
  - non-overlap succeeds
  - back-to-back succeeds
- `app/api/v1/rentalos.py::_apply_payment_summary`
  - advance increases `advance_paid`
  - balance reduces `balance_due` not below 0
  - security deposit increases `security_deposit`
  - refund reduces `security_deposit` not below 0
  - extra charge increases `total_amount` if present
- `app/utils/rentalos_azure_blob.py::build_rentalos_blob_name`
  - safe UUID-based paths
  - expected folder names
  - no original filename in path
- `app/utils/rentalos_azure_blob.py::validate_rentalos_upload`
  - rejects unsupported content type
  - rejects oversized content
  - rejects empty file

## High-priority integration/API tests

### RentalOS access

1. Owner can access own shop.
2. Owner cannot access another shop.
3. Active `RentalStaff` can access assigned shop.
4. Inactive `RentalStaff` cannot access.
5. Staff cannot access unassigned shop.
6. Booking-scoped endpoints use `RentalBooking.shop_id`, not request body.
7. Customer-scoped flag endpoints use `RentalCustomer.shop_id`.
8. Owner can create/list/update/deactivate staff.
9. Staff cannot access staff management endpoints.
10. `/api/v1/rentalos/me` returns owner shops and active staff shops only.

Suggested routes:

- `GET /api/v1/rentalos/catalog/vehicles`
- `GET /api/v1/rentalos/me`
- `POST /api/v1/rentalos/staff`
- `GET /api/v1/rentalos/staff?shop_id=...`
- `PATCH /api/v1/rentalos/staff/{staff_id}`
- `GET /api/v1/rentalos/bookings/{booking_id}`
- `GET /api/v1/rentalos/bookings/{booking_id}/documents`
- `POST /api/v1/rentalos/customers/{customer_id}/flags`

### Customer lookup/create

1. Search missing phone returns `found=false`.
2. Search existing phone returns customer summary.
3. Search includes previous booking count.
4. Search includes latest active flag.
5. Search includes latest note.
6. Same phone can be created in two different shops.
7. Same phone cannot be created twice in one shop.
8. Consent true sets `document_consent_at` / `marketing_consent_at`; false leaves timestamps null.

### Catalog availability

1. Available bike returns `available`.
2. `is_available=False` returns `unavailable`.
3. `maintenance_status="maintenance"` returns `maintenance`.
4. Online pending conflict returns `booked`.
5. RentalOS confirmed conflict returns `booked`.
6. Missing only one of `start_time`/`end_time` returns 400.
7. `start_time >= end_time` returns 400.

### Booking conflict

1. Online pending `Booking` blocks `RentalBooking`.
2. Online confirmed `Booking` blocks `RentalBooking`.
3. Online completed `Booking` does not block.
4. RentalBooking draft/confirmed/active blocks.
5. RentalBooking completed/cancelled does not block.
6. Non-overlapping booking succeeds.
7. Back-to-back booking succeeds.
8. Bike from another shop in request returns 400.
9. Unavailable or maintenance bike returns 409.
10. Existing customer is reused by `(shop_id, phone_number)`.
11. New customer is created when phone is missing.
12. Optional booking note creates `RentalBookingNote`.

### Upload validation

Mock Azure upload or monkeypatch `upload_rentalos_blob` to avoid network.

Documents:

1. DL/ID upload accepts JPEG.
2. DL/ID upload accepts PNG.
3. DL/ID upload accepts WebP.
4. DL/ID upload accepts PDF.
5. Invalid `document_type` returns 400.
6. Unsupported content type returns 400.
7. Oversized file returns 400.
8. Empty file returns 400.
9. Other shop cannot upload or view docs.
10. Stored `file_name` preserves original name; blob path should not use original name.

Handover photos:

1. Handover upload accepts JPEG/PNG/WebP.
2. Handover upload rejects PDF.
3. Oversized file rejected.
4. Other shop cannot view photos.
5. Invalid latitude rejected.
6. Invalid longitude rejected.
7. Location fields optional.
8. `location_permission_granted=false` does not require lat/lng.

### Payment summary

1. Advance increases `advance_paid`.
2. Balance reduces `balance_due` but not below 0.
3. Security deposit increases `security_deposit`.
4. Refund reduces `security_deposit` but not below 0.
5. Extra charge increases `total_amount` if present.
6. Invalid payment type returns 400.
7. Invalid method returns 400.
8. Invalid status returns 400.
9. Non-positive amount returns 400.
10. Cancelled booking rejects payment.
11. Completed booking rejects payment.
12. `RentalPayment` rows are created; marketplace `Payment` rows are not.

### Trip completion

1. Confirmed booking can complete.
2. Active booking can complete if current code allows direct status fixture.
3. Completed booking cannot complete again.
4. Cancelled booking cannot complete.
5. Completion note is created.
6. Completion flag updates `RentalCustomer.current_flag_status`.
7. Negative flag requires note.
8. Completed booking no longer blocks availability.

### Notes and flags

1. Empty booking note returns 400.
2. Booking note creates row with `created_by_user_id`.
3. Other shop cannot list notes.
4. Valid customer flag creates row.
5. Active flag updates `current_flag_status`.
6. Inactive flag does not update `current_flag_status`.
7. Invalid flag type returns 400.
8. Invalid severity returns 400.
9. Negative flag without note returns 400.
10. Other shop cannot list/create flags.

## Auth/access tests

Marketplace:

1. Login rejects unverified email.
2. Login returns bearer token for verified user.
3. `GET /api/v1/users/{user_id}` rejects other user.
4. Shop owner can create shop.
5. Customer cannot create shop.
6. Owner cannot update another owner's shop.
7. Owner cannot update another owner's bike.
8. Owner cannot manage another owner's inventory.
9. Customer cannot manage shop-owner booking actions.
10. Customer cannot access other customer's payment.

RentalOS:

1. Owner can access own shop.
2. Owner cannot access another shop.
3. Active staff can access assigned shop.
4. Inactive staff cannot access.
5. Staff cannot access unassigned shop.
6. Other shop cannot access documents/photos/payments/notes/flags.
7. Owner can manage staff for own shop.
8. Owner cannot manage staff for another shop.
9. Active staff cannot manage staff.
10. Inactive staff is omitted from `/api/v1/rentalos/me`.

## Cross-shop isolation tests

Create:

- Owner A, Shop A, Bike A.
- Owner B, Shop B, Bike B.
- Staff A assigned to Shop A.
- Staff B assigned inactive to Shop A.
- RentalCustomer A under Shop A.
- RentalBooking A under Shop A.

Then assert:

- Owner B gets 403 for Shop A RentalOS routes.
- Staff A gets 200 for Shop A and 403 for Shop B.
- Staff B gets 403 for Shop A.
- Owner A cannot pass Bike B into Shop A booking create.
- Owner B cannot view Shop A documents/photos/notes/payments.

## Existing marketplace regression tests

High priority:

1. Existing online booking creation still works.
2. Online booking creation still creates `Booking`, not `RentalBooking`.
3. Online booking creation still updates `BikeInventory`.
4. Razorpay payment flow still uses `Payment`, not `RentalPayment`.
5. Razorpay webhook still updates online `Booking`/`Payment`.
6. Bike image upload still calls Cloudinary utility.
7. Shop image upload still calls Cloudinary utility.
8. RentalOS Azure utility is not used by marketplace image uploads.
9. Existing search/shop/bike public endpoints still respond.

## Suggested test data fixtures

Fixture names:

- `verified_customer`
- `verified_owner`
- `other_owner`
- `staff_user`
- `inactive_staff_user`
- `owner_shop`
- `other_shop`
- `owner_bike`
- `other_bike`
- `bike_inventory`
- `rental_staff`
- `inactive_rental_staff`
- `rental_customer`
- `rental_booking`
- `auth_headers(user)`

Implementation notes:

- For auth headers, use `create_access_token(data={"user_id": user.id, "role": "user"})`.
- For file upload tests, use `io.BytesIO`.
- Monkeypatch Azure with a fake `RentalOSBlobUpload(blob_name="...", blob_url="...")`.
- Avoid real Cloudinary/Razorpay/Azure network calls in tests.

## Suggested smoke test sequence

1. Create owner user and shop.
2. Create bike for owner shop.
3. Create active `RentalStaff` for same shop.
4. Staff requests catalog.
5. Staff searches missing phone.
6. Staff creates RentalOS booking with new phone.
7. Staff uploads document with mocked Azure.
8. Staff uploads handover photo with mocked Azure.
9. Staff records advance payment.
10. Staff completes booking with note.
11. Staff adds/reads customer flag.
12. Owner lists booking/documents/photos/payments/notes/flags.
13. Other owner receives 403 for each shop-scoped route.

## Commands to run

Suggested first commands:

```bash
pytest
```

If login rate-limit failures appear:

```bash
.venv/bin/pytest tests/test_auth.py tests/test_users.py -vv
```

Then add focused RentalOS tests:

```bash
.venv/bin/pytest tests/test_rentos_access.py tests/test_rentos_booking_conflicts.py -vv
```

Future RentalOS test files should use the `test_rentos_` prefix.
