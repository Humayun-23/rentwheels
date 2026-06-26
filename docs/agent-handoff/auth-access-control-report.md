# Auth And Access Control Report

## Login/auth flow

Files:

- `app/api/v1/auth.py`
- `app/api/v1/oauth2.py`
- `app/utils/utils.py`
- `app/db/models.py::User`

Email/password login:

1. `POST /api/v1/login` calls `app/api/v1/auth.py::login`.
2. It looks up `User` by `email == username`.
3. It verifies the password with `app.utils.utils.verify_password`.
4. It rejects users with `is_email_verified == False`.
5. It creates a JWT through `app/api/v1/oauth2.py::create_access_token(data={"user_id": user.id, "role": "user"})`.

Google login:

1. `POST /api/v1/google` calls `app/api/v1/auth.py::google_login`.
2. It verifies Google credential with `google.oauth2.id_token.verify_oauth2_token`.
3. It creates a local verified `User` if one does not exist.
4. It issues the same app JWT shape with `user_id` and `role="user"`.

Rate limiting:

- `/login`, `/google`, `/users/`, and `/users/verify-email/resend` use SlowAPI limits.
- Known test concern: rate limiter state can affect repeated login tests.

## JWT/token behavior

File: `app/api/v1/oauth2.py`

- `oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/v1/login')`.
- `SECRET_KEY`, `ALGORITHM`, and `ACCESS_TOKEN_EXPIRE_MINUTES` come from `app.config.settings`.
- `create_access_token(data)` copies the payload, adds `exp`, then encodes with PyJWT.
- `verify_access_token(token, credentials_exception)` decodes the token and extracts `user_id` and optional `role`.
- `Settings.validate_algorithm()` forces algorithm to `HS256` if env provides something else.

Token payload fields observed:

- `user_id`
- `role`
- `exp`

Observed/confirmed:

- Token revocation/refresh is not implemented in observed code.
- Access token expiry value depends on environment.

## `get_current_user` dependency

File/function: `app/api/v1/oauth2.py::get_current_user`

Behavior:

- Requires bearer token from `OAuth2PasswordBearer`.
- Calls `verify_access_token`.
- If token role is present and not `"user"`, returns 403.
- Loads `User` by `token_data.user_id`.
- Returns 401 if token invalid or user missing.

This dependency is used across marketplace and RentalOS endpoints.

## User roles/user_type patterns

Model column: `User.user_type`

Observed values:

- `customer`
- `shop_owner`
- `shop_staff`
- `admin` is referenced in `app/api/v1/booking.py::list_bookings`, but `UserCreate` only allows `customer` and `shop_owner`.

Common access patterns:

- Customer-only: marketplace booking create, payments, review creation.
- Shop-owner-only: shop create, bike CRUD, inventory management, shop dashboard/analytics, booking confirm/reject/complete/return.
- Self-only: user profile get/update.
- Public: shop list/detail, bike detail/list, search, stats, review list, password reset request/confirm, email verification.
- RentalOS staff users are created internally by owner-only `POST /api/v1/rentalos/staff`; public signup does not allow `shop_staff`.

Confirmed project status:

- No out-of-band `admin` users are expected to exist. The `admin` branch in `list_bookings()` appears unreachable unless data is manually changed.

## Shop owner access pattern

The dominant shop isolation rule is:

```python
Shop.owner_id == current_user.id
```

Examples:

- `app/api/v1/shops.py::update_shop`
- `app/api/v1/shops.py::delete_shop`
- `app/api/v1/listing.py::create_bike`
- `app/api/v1/listing.py::update_bike`
- `app/api/v1/inventory.py::get_shop_inventory`
- `app/api/v1/booking.py::verify_shop_ownership`

Expected behavior:

- Owners can manage only shops they own.
- Owners can manage bikes/inventory/bookings only through owned shops.
- Non-owners receive 403.

## RentalOS owner/staff access pattern

File: `app/api/v1/rentalos.py`

Core functions:

- `get_user_rental_staff_membership(db, user_id, shop_id)`
- `get_rentalos_shop_access(db, shop_id, current_user)`
- `assert_rentalos_shop_access(db, shop_id, current_user)`
- `assert_rentalos_owner_access(db, shop_id, current_user)`
- `get_accessible_rental_booking(db, booking_id, current_user)`
- `get_accessible_rental_customer(db, customer_id, current_user)`

Access rule:

1. Load `Shop` by `shop_id`.
2. If `shop.owner_id == current_user.id`, allow as owner.
3. Else look for `RentalStaff` where `user_id == current_user.id`, `shop_id == shop_id`, and `is_active == True`.
4. If active staff membership exists, allow.
5. Otherwise return 403.

Booking/document/payment/note access:

- Load `RentalBooking` by `booking_id`.
- Use `booking.shop_id` for access checks.
- Do not trust `shop_id` from request body for these booking-scoped routes.

Customer flag access:

- Load `RentalCustomer` by `customer_id`.
- Use `customer.shop_id` for access checks.

Staff management access:

- `POST /api/v1/rentalos/staff`, `GET /api/v1/rentalos/staff`, and `PATCH /api/v1/rentalos/staff/{staff_id}` are owner-only.
- They use `assert_rentalos_owner_access`, which requires `Shop.owner_id == current_user.id`.
- Active staff can use counter APIs but cannot manage staff.
- Inactive staff may still log in through normal auth, but `/api/v1/rentalos/me` omits inactive memberships and counter APIs reject inactive staff.
- `GET /api/v1/rentalos/me` returns owner shops and active staff shops for frontend routing.

## Where authorization checks are implemented

- `app/api/v1/oauth2.py`: JWT validation and current user loading.
- `app/api/v1/shops.py`: shop owner checks.
- `app/api/v1/listing.py`: bike/service-log owner checks.
- `app/api/v1/inventory.py`: inventory owner checks.
- `app/api/v1/booking.py`: customer ownership and `verify_shop_ownership()`.
- `app/api/v1/payments.py`: customer payment ownership through `Booking.customer_id`.
- `app/api/v1/reviews.py`: customer-only and own-review checks.
- `app/api/v1/rentalos.py`: owner/staff shop access and booking/customer scoped access helpers.

## Cross-shop isolation expectations

Marketplace:

- A shop owner cannot create/update/delete bikes for another owner shop.
- A shop owner cannot confirm/reject/complete/return bookings for another owner shop.
- A shop owner cannot view another owner shop inventory.
- Customers cannot view/update/cancel other customers' bookings.
- Customers cannot view/pay/refund other customers' payments.

RentalOS:

- Shop owner can access own shop RentalOS records.
- Owner cannot access another shop RentalOS records unless also active staff there.
- Active `RentalStaff` can access assigned shop RentalOS records.
- Inactive staff cannot access assigned shop records.
- Staff cannot access unassigned shops.
- Booking-scoped file/payment/note routes must authorize by `RentalBooking.shop_id`.
- Customer-scoped flag routes must authorize by `RentalCustomer.shop_id`.

## Known risks or missing tests

- RentalOS tests exist under the `tests/test_rentos_*.py` naming convention.
- Fresh `.venv/bin/pytest` run after PR5 passed: `36 passed`.
- `admin` branch in `list_bookings()` is expected to be unreachable from public registration schema because no admin users exist outside registration.
- RentalOS file URLs are returned directly. Access to private blob contents depends on storage configuration until signed/authenticated download is implemented.
- Marketplace/RentalOS availability conflict checks are not centralized.

## Recommended auth/access tests

Marketplace:

1. Customer can create online booking; shop owner cannot.
2. Customer cannot view/update/cancel another customer's booking.
3. Owner can confirm/reject/complete/return booking for own shop bike.
4. Owner cannot manage booking for another owner's shop bike.
5. Owner cannot update/delete another owner's shop.
6. Owner cannot update/delete another owner's bike or inventory.
7. Customer cannot access shop-owner-only endpoints.
8. Payment create/verify/refund rejects bookings not owned by the customer.

RentalOS:

1. Owner can access own shop catalog, customers, bookings, files, payments, notes, flags.
2. Owner cannot access another shop RentalOS data.
3. Active `RentalStaff` can access assigned shop.
4. Inactive `RentalStaff` cannot access assigned shop.
5. Staff cannot access unassigned shop.
6. Booking-scoped upload/list/payment/note routes reject users from other shops.
7. Customer flag routes reject users from other shops.
8. `shop_id` in request body never bypasses booking/customer-derived access checks.
9. Owner can create/list/update/deactivate staff for own shop.
10. Staff cannot access staff management endpoints.
11. Inactive staff does not appear in `/api/v1/rentalos/me` and cannot access counter endpoints.
