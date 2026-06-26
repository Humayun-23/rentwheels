# Database Models Report

Primary model file: `app/db/models.py`

Relevant RentalOS migration: `alembic/versions/7c3a91d4e8f2_add_rentalos_database_foundation.py`

## User

- Class/table: `User` / `users`
- Purpose: platform user record for customers and shop owners.
- Important columns: `id`, `email`, `password`, `firstname`, `lastname`, `phone_number`, `user_type`, `is_email_verified`, `created_at`, `updated_at`.
- Foreign keys: none.
- Relationships: `shops`, `bookings`, `rental_staff_memberships`.
- Constraints/indexes: `email` unique/indexed; `id` indexed.
- Cascade behavior: shop and booking child cascades are configured from child FKs/relationships, not directly here.
- APIs: auth/user, shops, booking, payments, RentalOS staff access.
- Audit/testing concerns: verify user_type enforcement, email verification login requirement, profile self-access only, token role handling.

## Shop

- Class/table: `Shop` / `shops`
- Purpose: rental shop owned by a `User`.
- Important columns: `id`, `name`, `description`, `owner_id`, `phone_number`, `upi_id`, `address`, `city`, `state`, `zip_code`, `opening_time`, `closing_time`, `is_active`, timestamps.
- Foreign keys: `owner_id -> users.id` with `ondelete="CASCADE"`.
- Relationships: `owner`, `bikes`, `image`, `rental_staff`, `rental_customers`, `rental_bookings`.
- Constraints/indexes: `owner_id` indexed; `id` indexed.
- Cascade behavior: `bikes`, `image`, `rental_staff`, `rental_customers`, `rental_bookings` use `cascade="all, delete-orphan"`.
- APIs: shop CRUD, dashboard/analytics, bike ownership checks, inventory checks, RentalOS shop access.
- Audit/testing concerns: cross-shop isolation depends heavily on `Shop.owner_id == current_user.id`.

## ShopImage

- Class/table: `ShopImage` / `shop_images`
- Purpose: Cloudinary-backed shop photo metadata.
- Important columns: `id`, `shop_id`, `image_url`, `created_at`.
- Foreign keys: `shop_id -> shops.id` with `ondelete="CASCADE"`.
- Relationships: `shop`.
- Constraints/indexes: `shop_id` indexed; `id` indexed.
- Cascade behavior: deleted with parent shop through relationship/FK.
- APIs: `app/api/v1/shops.py::upload_shop_image`.
- Audit/testing concerns: ensure Cloudinary behavior remains separate from RentalOS Azure uploads.

## Bike

- Class/table: `Bike` / `bikes`
- Purpose: rentable vehicle record. Despite name, supports `bike_type` including scooters/cars.
- Important columns: `id`, `shop_id`, `name`, `model`, `bike_type`, `engine_cc`, `description`, `price_per_hour`, `price_per_day`, `condition`, `is_available`, `maintenance_status`, timestamps.
- Foreign keys: `shop_id -> shops.id` with `ondelete="CASCADE"`.
- Relationships: `shop`, `bookings`, `inventory`, `image`, `service_logs`, `rental_bookings`.
- Constraints/indexes: `shop_id` indexed; `id` indexed.
- Cascade behavior: `bookings`, `inventory`, `image`, `service_logs`, `rental_bookings` use `cascade="all, delete-orphan"`.
- APIs: listing, search, inventory, booking, RentalOS catalog/booking.
- Audit/testing concerns: RentalOS uses `Bike.is_available` and `maintenance_status`; online booking also uses `BikeInventory`.

## BikeImage

- Class/table: `BikeImage` / `bike_images`
- Purpose: Cloudinary-backed vehicle image metadata.
- Important columns: `id`, `bike_id`, `image_url`, `created_at`.
- Foreign keys: `bike_id -> bikes.id` with `ondelete="CASCADE"`.
- Relationships: `bike`.
- Constraints/indexes: `bike_id` indexed; `id` indexed.
- Cascade behavior: deleted with parent bike through relationship/FK.
- APIs: `app/api/v1/listing.py::upload_bike_images`, catalog image output.
- Audit/testing concerns: max 3 image rule enforced in API, not model.

## BikeInventory

- Class/table: `BikeInventory` / `bike_inventory`
- Purpose: stock/count tracking for marketplace bookings.
- Important columns: `id`, `bike_id`, `shop_id`, `total_quantity`, `available_quantity`, `rented_quantity`, timestamps.
- Foreign keys: `bike_id -> bikes.id`, `shop_id -> shops.id`, both `ondelete="CASCADE"`.
- Relationships: `bike`.
- Constraints/indexes: `bike_id` unique/indexed; `shop_id` indexed; `id` indexed.
- Cascade behavior: deleted with bike/shop through FK/relationship.
- APIs: inventory router, listing bike creation, online booking create/cancel/reject/return.
- Audit/testing concerns: online booking decrements/restores counters. RentalOS does not mutate this inventory. Verify counters do not go negative and return/complete semantics are consistent.

## Booking

- Class/table: `Booking` / `bookings`
- Purpose: online marketplace customer booking.
- Important columns: `id`, `customer_id`, `bike_id`, `start_time`, `end_time`, `magic_token`, `status`, `utr_number`, `token_amount`, `total_price`, timestamps, `confirmed_at`, `completed_at`.
- Foreign keys: `customer_id -> users.id`, `bike_id -> bikes.id`, both `ondelete="CASCADE"`.
- Relationships: `customer`, `bike`.
- Constraints/indexes: `customer_id`, `bike_id`, `id` indexed.
- Cascade behavior: deleted with user/bike through FK/relationship.
- APIs: booking router, payments router, reviews, statistics, RentalOS conflict checks.
- Audit/testing concerns: conflict statuses should stay aligned across marketplace and RentalOS. Online creation checks `["pending", "confirmed", "paid"]`; RentalOS conflict code checks `["pending", "paid", "confirmed"]`.

## Payment

- Class/table: `Payment` / `payment`
- Purpose: Razorpay payment/refund state for online marketplace `Booking`.
- Important columns: `id`, `order_id`, `payment_id`, `refund_id`, `booking_id`, `amount`, `refunded_amount`, `currency`, `razorpay_signature`, `status`, timestamps.
- Foreign keys: `booking_id -> bookings.id` with `ondelete="CASCADE"`.
- Relationships: none declared back to `Booking`.
- Constraints/indexes: `order_id`, `payment_id`, `refund_id` unique/indexed; `booking_id` indexed.
- Cascade behavior: deleted with booking through FK.
- APIs: `app/api/v1/payments.py`.
- Audit/testing concerns: must remain separate from `RentalPayment`; Razorpay webhooks should never mutate RentalOS payments/bookings.

## ServiceLog

- Class/table: `ServiceLog` / `service_logs`
- Purpose: maintenance/service history for vehicles.
- Important columns: `id`, `bike_id`, `description`, `cost`, `service_date`, `created_at`.
- Foreign keys: `bike_id -> bikes.id` with `ondelete="CASCADE"`.
- Relationships: `bike`.
- Constraints/indexes: `bike_id`, `id` indexed.
- Cascade behavior: deleted with bike through relationship/FK.
- APIs: service-log endpoints in `app/api/v1/listing.py`.
- Audit/testing concerns: owner-only enforcement.

## Review

- Class/table: `Review` / `reviews`
- Purpose: customer review for a shop after completed/returned marketplace booking.
- Important columns: `id`, `customer_id`, `shop_id`, `rating`, `comment`, timestamps.
- Foreign keys: `customer_id -> users.id`, `shop_id -> shops.id`, both `ondelete="CASCADE"`.
- Relationships: `shop`, `customer`.
- Constraints/indexes: `customer_id`, `shop_id`, `id` indexed.
- Cascade behavior: deleted with user/shop through FK.
- APIs: reviews router, shop dashboard metrics.
- Audit/testing concerns: duplicate review check is API-level only.

## PasswordResetToken

- Class/table: `PasswordResetToken` / `password_reset_tokens`
- Purpose: password reset tokens.
- Important columns: `id`, `user_id`, `token`, `expires_at`, `is_used`, `created_at`.
- Foreign keys: `user_id -> users.id` with `ondelete="CASCADE"`.
- Relationships: `user`.
- Constraints/indexes: `token` unique/indexed; `user_id` indexed.
- APIs: password reset router.
- Audit/testing concerns: token expiry and single-use behavior.

## EmailVerificationToken

- Class/table: `EmailVerificationToken` / `email_verification_tokens`
- Purpose: email verification tokens.
- Important columns: `id`, `user_id`, `token`, `expires_at`, `is_used`, `created_at`.
- Foreign keys: `user_id -> users.id` with `ondelete="CASCADE"`.
- Relationships: `user`.
- Constraints/indexes: `token` unique/indexed; `user_id` indexed.
- APIs: user verification endpoints.
- Audit/testing concerns: token expiry, resend invalidation, login before verification.

## RentalStaff

- Class/table: `RentalStaff` / `rental_staff`
- Purpose: RentalOS shop staff membership.
- Important columns: `id`, `shop_id`, `user_id`, `role`, `is_active`, timestamps.
- Foreign keys: `shop_id -> shops.id` and `user_id -> users.id`, both `ondelete="CASCADE"`.
- Relationships: `shop`, `user`, `bookings`.
- Constraints/indexes: unique `(shop_id, user_id)` named `uq_rental_staff_shop_user`; `shop_id`, `user_id`, `id` indexed.
- Cascade behavior: deleted with shop/user through FK; shop relationship also has delete-orphan.
- APIs: RentalOS access helpers, `/api/v1/rentalos/me`, and owner-only staff management endpoints.
- Audit/testing concerns: active staff can access assigned shop counter APIs only; inactive staff rejected. Staff management must remain owner-only.

## RentalCustomer

- Class/table: `RentalCustomer` / `rental_customers`
- Purpose: offline RentalOS customer record scoped to one shop.
- Important columns: `id`, `shop_id`, `phone_number`, `firstname`, `lastname`, `document_consent`, `document_consent_at`, `marketing_consent`, `marketing_consent_at`, `current_flag_status`, `created_by_user_id`, timestamps.
- Foreign keys: `shop_id -> shops.id` with `ondelete="CASCADE"`; `created_by_user_id -> users.id` with `ondelete="SET NULL"`.
- Relationships: `shop`, `created_by_user`, `bookings`, `flags`.
- Constraints/indexes: unique `(shop_id, phone_number)` named `uq_rental_customers_shop_phone`; `shop_id`, `phone_number`, `created_by_user_id`, `id` indexed.
- Cascade behavior: `bookings` and `flags` delete-orphan.
- APIs: RentalOS customer search/create, booking create, completion flags.
- Audit/testing concerns: phone uniqueness is shop-scoped; ensure another shop can use same phone.

## RentalCustomerFlag

- Class/table: `RentalCustomerFlag` / `rental_customer_flags`
- Purpose: shop-scoped RentalOS flag/history for walk-in customers.
- Important columns: `id`, `shop_id`, `customer_id`, `flag_type`, `severity`, `note`, `is_active`, `created_by_user_id`, timestamps.
- Foreign keys: `shop_id -> shops.id`, `customer_id -> rental_customers.id`, both cascade; `created_by_user_id -> users.id` SET NULL.
- Relationships: `shop`, `customer`, `created_by_user`.
- Constraints/indexes: `shop_id`, `customer_id`, `created_by_user_id`, `id` indexed.
- Cascade behavior: deleted with customer/shop through FK/relationship.
- APIs: RentalOS flag create/list, customer search latest flag.
- Audit/testing concerns: current flag status update is API logic; no model-level enum constraint.

## RentalBooking

- Class/table: `RentalBooking` / `rental_bookings`
- Purpose: offline RentalOS counter booking, separate from online `Booking`.
- Important columns: `id`, `shop_id`, `customer_id`, `bike_id`, `staff_id`, `start_time`, `end_time`, `status`, `total_amount`, `advance_paid`, `balance_due`, `security_deposit`, `completed_at`, timestamps.
- Foreign keys: `shop_id -> shops.id`, `customer_id -> rental_customers.id`, `bike_id -> bikes.id` cascade; `staff_id -> rental_staff.id` SET NULL.
- Relationships: `shop`, `customer`, `bike`, `staff`, `documents`, `handover_photos`, `payments`, `notes`.
- Constraints/indexes: `shop_id`, `customer_id`, `bike_id`, `staff_id`, `start_time`, `end_time`, `status`, `id` indexed.
- Cascade behavior: child documents/photos/payments/notes delete-orphan; parent FKs cascade as above.
- APIs: all RentalOS booking lifecycle endpoints.
- Audit/testing concerns: completed/cancelled should not block availability; statuses are strings without DB enum/check constraints.

## RentalBookingDocument

- Class/table: `RentalBookingDocument` / `rental_booking_documents`
- Purpose: sensitive RentalOS DL/ID document metadata.
- Important columns: `id`, `booking_id`, `document_type`, `file_url`, `file_name`, `content_type`, `uploaded_by_user_id`, `created_at`.
- Foreign keys: `booking_id -> rental_bookings.id` cascade; `uploaded_by_user_id -> users.id` SET NULL.
- Relationships: `booking`, `uploaded_by_user`.
- Constraints/indexes: `booking_id`, `uploaded_by_user_id`, `id` indexed.
- Cascade behavior: deleted with booking.
- APIs: RentalOS document upload/list.
- Audit/testing concerns: file_url currently returned directly; signed/authenticated access needed before production if direct URL is exposed.

## RentalHandoverPhoto

- Class/table: `RentalHandoverPhoto` / `rental_handover_photos`
- Purpose: customer-with-vehicle handover photo metadata plus optional location.
- Important columns: `id`, `booking_id`, `image_url`, `location_permission_granted`, `latitude`, `longitude`, `location_accuracy_meters`, `location_address`, `captured_at`, `uploaded_by_user_id`, `created_at`.
- Foreign keys: `booking_id -> rental_bookings.id` cascade; `uploaded_by_user_id -> users.id` SET NULL.
- Relationships: `booking`, `uploaded_by_user`.
- Constraints/indexes: `booking_id`, `uploaded_by_user_id`, `id` indexed.
- Cascade behavior: deleted with booking.
- APIs: RentalOS handover upload/list.
- Audit/testing concerns: validate lat/lng boundaries and that PDF is rejected.

## RentalPayment

- Class/table: `RentalPayment` / `rental_payments`
- Purpose: offline RentalOS payment ledger for advance/balance/security/refund/extra charge.
- Important columns: `id`, `booking_id`, `payment_type`, `amount`, `status`, `method`, `reference_number`, `paid_at`, `received_by_user_id`, timestamps.
- Foreign keys: `booking_id -> rental_bookings.id` cascade; `received_by_user_id -> users.id` SET NULL.
- Relationships: `booking`, `received_by_user`.
- Constraints/indexes: `booking_id`, `status`, `received_by_user_id`, `id` indexed.
- Cascade behavior: deleted with booking.
- APIs: RentalOS payment create/list.
- Audit/testing concerns: separate from Razorpay `Payment`; payment summary updates are API-level.

## RentalBookingNote

- Class/table: `RentalBookingNote` / `rental_booking_notes`
- Purpose: operational note for a RentalOS booking/customer interaction.
- Important columns: `id`, `booking_id`, `note`, `created_by_user_id`, `created_at`.
- Foreign keys: `booking_id -> rental_bookings.id` cascade; `created_by_user_id -> users.id` SET NULL.
- Relationships: `booking`, `created_by_user`.
- Constraints/indexes: `booking_id`, `created_by_user_id`, `id` indexed.
- Cascade behavior: deleted with booking.
- APIs: RentalOS booking note create/list, completion optional note, customer search latest note.
- Audit/testing concerns: note non-empty is API-level only.

## Migration notes

`alembic/versions/7c3a91d4e8f2_add_rentalos_database_foundation.py` creates all RentalOS tables above with indexes and unique constraints. It includes:

- `uq_rental_staff_shop_user`
- `uq_rental_customers_shop_phone`
- indexes on `rental_bookings.start_time`, `rental_bookings.end_time`, and `rental_bookings.status`
- `location_permission_granted` default false
- consent fields default false

Project status: production migrations are not applied yet. A clean Alembic upgrade should be run before deployment to confirm the full chain applies from `42ee243ff209`.
