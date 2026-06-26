# API Endpoints Report

Paths are final mounted API paths unless noted. Versioned routers are mounted in `app/main.py` with `/api/v1`.

## Auth/user endpoints (GoPanda)

| Method | Path | Router/file | Auth | Request | Response | Models touched | Side effects | Visible errors | Priority |
|---|---|---|---|---|---|---|---|---|---|
| POST | `/api/v1/login` | `app/api/v1/auth.py::login` | Public, rate-limited | `OAuth2PasswordRequestForm`: `username`, `password` | `Token` | `User` | JWT creation | 403 invalid credentials/email not verified | High |
| POST | `/api/v1/google` | `app/api/v1/auth.py::google_login` | Public, rate-limited | `GoogleLoginRequest` | `Token` | `User` | Creates Google user if absent, verifies email, JWT creation | 403 invalid Google token | Medium |
| POST | `/api/v1/users/` | `app/api/v1/users.py::create_user` | Public, rate-limited | `UserCreate` | `UserOut` | `User`, `EmailVerificationToken` | Hashes password, creates token, optional SMTP email | 400 duplicate/short password, 500 create failure | High |
| POST | `/api/v1/users/verify-email` | `app/api/v1/users.py::verify_email` | Public | `EmailVerificationRequest` | `EmailVerificationResponse` | `User`, `EmailVerificationToken` | Marks email/token verified, returns JWT | 400 invalid/expired token, 404 user missing | High |
| POST | `/api/v1/users/verify-email/resend` | `app/api/v1/users.py::resend_verification` | Public, rate-limited | `EmailVerificationResend` | `EmailVerificationResponse` | `User`, `EmailVerificationToken` | Invalidates old tokens, creates token, optional SMTP email | Generic success for missing user | Medium |
| GET | `/api/v1/users/{user_id}` | `app/api/v1/users.py::get_user_by_id` | Bearer user | path `user_id` | `UserOut` | `User` | None | 401, 403 if not same user, 404 | High |
| PUT | `/api/v1/users/{user_id}` | `app/api/v1/users.py::update_user` | Bearer user | path `user_id`, `UserUpdate` | `UserOut` | `User` | Updates own profile fields | 401, 403 if not same user, 404, 500 | High |
| POST | `/api/v1/password-reset/request` | `app/api/v1/passwordreset.py::request_password_reset` | Public | `PasswordResetRequest` | `PasswordResetResponse` | `User`, `PasswordResetToken` | Invalidates old reset tokens, creates new token, optional SMTP email | Generic success for missing email | Medium |
| POST | `/api/v1/password-reset/confirm` | `app/api/v1/passwordreset.py::confirm_password_reset` | Public | `PasswordResetConfirm` | `PasswordResetResponse` | `User`, `PasswordResetToken` | Hashes new password, marks token used | 400 invalid/expired/short password, 404 user missing | Medium |

## Shop endpoints

| Method | Path | Router/file | Auth | Request | Response | Models touched | Side effects | Visible errors | Priority |
|---|---|---|---|---|---|---|---|---|---|
| POST | `/api/v1/shops/` | `app/api/v1/shops.py::create_shop` | Bearer `shop_owner` | `ShopCreate` | `ShopOut` | `Shop` | Creates shop with `owner_id=current_user.id` | 403 non-owner | High |
| GET | `/api/v1/shops/dashboard-metrics` | `app/api/v1/shops.py::get_dashboard_metrics` | Bearer `shop_owner` | none | dict | `Shop`, `Bike`, `Booking`, `Review` | Aggregates owner-shop metrics | 403 non-owner | Medium |
| GET | `/api/v1/shops/analytics` | `app/api/v1/shops.py::get_analytics` | Bearer `shop_owner` | none | dict | `Shop`, `Bike`, `Booking` | Aggregates 30-day owner-shop analytics | 403 non-owner | Medium |
| GET | `/api/v1/shops/me` | `app/api/v1/shops.py::get_my_shops` | Bearer `shop_owner` | query `skip`, `limit` | `list[ShopOut]` | `Shop` | None | 403 non-owner | High |
| GET | `/api/v1/shops/{shop_id}` | `app/api/v1/shops.py::get_shop` | Public | path `shop_id` | `ShopOut` | `Shop` | None | 404 | Medium |
| GET | `/api/v1/shops/` | `app/api/v1/shops.py::get_all_shops` | Public | query `skip`, `limit` | `list[ShopOut]` | `Shop` | None | None explicit | Low |
| PUT | `/api/v1/shops/{shop_id}` | `app/api/v1/shops.py::update_shop` | Bearer owner | `ShopUpdate` | `ShopOut` | `Shop` | Updates owned shop | 403 not owner, 404 | High |
| DELETE | `/api/v1/shops/{shop_id}` | `app/api/v1/shops.py::delete_shop` | Bearer owner | path `shop_id` | 204 | `Shop` | Deletes shop; cascades configured relationships | 403 not owner, 404 | High |

## Bike/vehicle endpoints

| Method | Path | Router/file | Auth | Request | Response | Models touched | Side effects | Visible errors | Priority |
|---|---|---|---|---|---|---|---|---|---|
| POST | `/api/v1/bikes/` | `app/api/v1/listing.py::create_bike` | Bearer `shop_owner` owner | `BikeCreate` | `BikeOut` | `Bike`, `Shop`, `BikeInventory` | Creates bike and inventory row | 403 non-owner/not shop owner, 404 shop | High |
| GET | `/api/v1/bikes/{bike_id}` | `app/api/v1/listing.py::get_bike` | Public | path `bike_id` | `BikeOut` | `Bike` | None | 404 | Medium |
| GET | `/api/v1/bikes/shop/{shop_id}` | `app/api/v1/listing.py::get_shop_bikes` | Public | path `shop_id`, query `skip`, `limit` | `list[BikeOut]` | `Shop`, `Bike` | None | 404 shop | Medium |
| GET | `/api/v1/bikes/{bike_id}/full-details` | `app/api/v1/listing.py::get_bike_full_details` | Public | path `bike_id` | dict | `Bike`, `BikeInventory`, `Shop`, `Review` | None | 404 bike | Medium |
| PUT | `/api/v1/bikes/{bike_id}` | `app/api/v1/listing.py::update_bike` | Bearer shop owner | `BikeUpdate` | `BikeOut` | `Bike`, `Shop` | Updates owned bike | 403 not owner, 404 | High |
| DELETE | `/api/v1/bikes/{bike_id}` | `app/api/v1/listing.py::delete_bike` | Bearer shop owner | path `bike_id` | 204 | `Bike`, `Shop` | Deletes bike; cascades configured children | 403 not owner, 404 | High |
| POST | `/api/v1/bikes/{bike_id}/service-logs` | `app/api/v1/listing.py::create_service_log` | Bearer shop owner | `ServiceLogCreate` | `ServiceLogOut` | `Bike`, `Shop`, `ServiceLog` | Creates service log | 403 not owner, 404 bike | Medium |
| GET | `/api/v1/bikes/{bike_id}/service-logs` | `app/api/v1/listing.py::get_service_logs` | Bearer shop owner | path `bike_id` | `list[ServiceLogOut]` | `Bike`, `Shop`, `ServiceLog` | None | 403 not owner, 404 bike | Medium |
| DELETE | `/api/v1/bikes/{bike_id}/service-logs/{log_id}` | `app/api/v1/listing.py::delete_service_log` | Bearer shop owner | path ids | 204 | `Bike`, `Shop`, `ServiceLog` | Deletes service log | 403 not owner, 404 bike/log | Medium |
| GET | `/api/v1/search/vehicles` | `app/api/v1/searchvehicle.py::search_vehicles` | Public | query `q`, `vehicle_type`, `engine_cc`, `cc_min`, `cc_max`, `is_available`, `shop_id`, `skip`, `limit` | `List[BikeOut]` | `Bike`, `BikeInventory`, `Shop` | None | None explicit | Medium |
| GET | `/api/v1/search/vehicles/type/{vehicle_type}` | `app/api/v1/searchvehicle.py::search_vehicles_by_type` | Public | path `vehicle_type`, query `is_available`, `shop_id`, `skip`, `limit` | `List[BikeOut]` | `Bike`, `BikeInventory` | None | Validation for literal type | Low |

## Inventory endpoints

| Method | Path | Router/file | Auth | Request | Response | Models touched | Side effects | Visible errors | Priority |
|---|---|---|---|---|---|---|---|---|---|
| POST | `/api/v1/inventory/` | `app/api/v1/inventory.py::create_inventory` | Bearer shop owner | `BikeInventoryCreate` | `BikeInventoryOut` | `Bike`, `Shop`, `BikeInventory` | Creates inventory row | 400 duplicate/shop mismatch, 403, 404 | Medium |
| GET | `/api/v1/inventory/bike/{bike_id}` | `app/api/v1/inventory.py::get_inventory_by_bike` | Bearer shop owner | path `bike_id` | `BikeInventoryOut` | `BikeInventory`, `Bike`, `Shop` | None | 403 not owner, 404 | Medium |
| GET | `/api/v1/inventory/shop/{shop_id}` | `app/api/v1/inventory.py::get_shop_inventory` | Bearer shop owner | path `shop_id`, query `skip`, `limit` | `list[BikeInventoryOut]` | `Shop`, `BikeInventory`, `Bike` | None | 403 not owner, 404 | Medium |
| GET | `/api/v1/inventory/available/{bike_id}` | `app/api/v1/inventory.py::check_availability` | Public | path `bike_id` | `InventoryAvailability` | `BikeInventory` | None | 404 no inventory | Medium |
| PUT | `/api/v1/inventory/{bike_id}` | `app/api/v1/inventory.py::update_inventory` | Bearer shop owner | `BikeInventoryUpdate` | `BikeInventoryOut` | `BikeInventory`, `Bike`, `Shop` | Updates total/available quantity | 400 total below rented, 403, 404 | High |
| GET | `/api/v1/inventory/availability/timerange` | `app/api/v1/inventory.py::check_availability_range` | Public | query `shop_id`, `start_time`, `end_time` | `list[InventoryAvailability]` | `Bike`, `BikeInventory`, `Booking` | None | None explicit | Medium |

## Booking endpoints

| Method | Path | Router/file | Auth | Request | Response | Models touched | Side effects | Visible errors | Priority |
|---|---|---|---|---|---|---|---|---|---|
| POST | `/api/v1/bookings/` | `app/api/v1/booking.py::create_booking` | Bearer `customer`, rate-limited | `BookingCreate`, background tasks | `BookingOut` | `Booking`, `Bike`, `BikeInventory`, `Shop`, `User` | Locks inventory, creates pending booking, decrements availability, sends receipt email | 400 time/availability/conflict, 403 non-customer, 404 bike | High |
| GET | `/api/v1/bookings/user/` | `app/api/v1/booking.py::get_user_bookings` | Bearer user | query `skip`, `limit` | `list[BookingOut]` | `Booking` | None | 401 | Medium |
| GET | `/api/v1/bookings/` | `app/api/v1/booking.py::list_bookings` | Bearer user | query `skip`, `limit` | `list[BookingOut]` | `Booking`, `Bike`, `Shop` | Customers see own; owners see owned-shop bookings; admin sees all | 403 unknown role | High |
| GET | `/api/v1/bookings/{booking_id}` | `app/api/v1/booking.py::get_booking` | Bearer user | path `booking_id` | `BookingOut` | `Booking`, `Bike`, `Shop` | None | 403 not owner/customer, 404 | High |
| PUT | `/api/v1/bookings/{booking_id}` | `app/api/v1/booking.py::update_booking` | Bearer customer owner | `BookingUpdate` | `BookingOut` | `Booking`, `Bike`, `BikeInventory` | Updates pending booking times/price | 400 status/time/conflict, 403 not customer owner, 404 | High |
| DELETE | `/api/v1/bookings/{booking_id}` | `app/api/v1/booking.py::cancel_booking` | Bearer customer owner | path `booking_id` | 204 | `Booking`, `BikeInventory`, `Payment` | Cancels booking, restores inventory for active statuses | 400 paid/completed/cancelled, 403, 404 | High |
| POST | `/api/v1/bookings/{booking_id}/confirm` | `app/api/v1/booking.py::confirm_booking` | Bearer shop owner | path `booking_id` | `BookingOut` | `Booking`, `Bike`, `Shop` | Sets status confirmed and `confirmed_at` | 400 non-pending, 403, 404 | High |
| POST | `/api/v1/bookings/{booking_id}/reject` | `app/api/v1/booking.py::reject_booking` | Bearer shop owner | path `booking_id`, background tasks | `BookingOut` | `Booking`, `Bike`, `Shop`, `BikeInventory`, `User` | Sets cancelled, restores inventory, sends cancellation email | 400 invalid status, 403, 404 | High |
| POST | `/api/v1/bookings/{booking_id}/complete` | `app/api/v1/booking.py::complete_booking` | Bearer shop owner | path `booking_id` | `BookingOut` | `Booking`, `Bike`, `Shop` | Sets completed/completed_at; does not restore inventory | 400 invalid status, 403, 404 | High |
| POST | `/api/v1/bookings/{booking_id}/return` | `app/api/v1/booking.py::return_booking` | Bearer shop owner | path `booking_id` | `BookingOut` | `Booking`, `Bike`, `Shop`, `BikeInventory` | Sets returned, restores inventory | 400 invalid status, 403, 404 | High |
| GET | `/api/v1/bookings/{booking_id}/magic-action` | `app/api/v1/booking.py::magic_action` | Public token query | query `action`, `token` | HTML | `Booking`, `BikeInventory`, `User`, `Bike` | For `reject`, cancels booking, restores inventory, sends cancellation email | HTML invalid/not found/cancelled/unknown | Medium |

## Payment endpoints

| Method | Path | Router/file | Auth | Request | Response | Models touched | Side effects | Visible errors | Priority |
|---|---|---|---|---|---|---|---|---|---|
| POST | `/api/v1/payments/` | `app/api/v1/payments.py::create_payment` | Bearer `customer` | `PaymentOrderCreate` | `PaymentOrderOut` | `Booking`, `Payment` | Calls Razorpay order API, creates/reuses `Payment` | 400 invalid booking status/amount, 403, 404, 500 keys, 502 Razorpay | High |
| POST | `/api/v1/payments/verify` | `app/api/v1/payments.py::verify_payment` | Bearer `customer` | `PaymentVerify` | dict | `Payment`, `Booking` | Verifies signature, marks payment and booking paid | 400 invalid signature, 403, 404 | High |
| PUT | `/api/v1/payments/cancel/{order_id}` | `app/api/v1/payments.py::cancel_payment` | Bearer `customer` | path `order_id` | dict | `Payment`, `Booking` | Marks unpaid payment cancelled | 400 paid payment, 403, 404 | Medium |
| GET | `/api/v1/payments/{order_id}` | `app/api/v1/payments.py::get_payment` | Bearer `customer` | path `order_id` | `PaymentOut` | `Payment`, `Booking` | None | 403 not own booking, 404 | Medium |
| GET | `/api/v1/payments/booking/{booking_id}` | `app/api/v1/payments.py::get_payment_for_booking` | Bearer `customer` | path `booking_id` | `PaymentOut` | `Booking`, `Payment` | None | 404 booking/payment | Medium |
| POST | `/api/v1/payments/refund` | `app/api/v1/payments.py::refund_payment` | Bearer `customer` | `RefundCreate` | `PaymentOut` | `Payment`, `Booking` | Calls Razorpay refund API, updates payment and booking refund status | 400 invalid refund/payment, 403, 404, 502 | High |
| POST | `/api/v1/payments/webhook` | `app/api/v1/payments.py::razorpay_webhook` | Razorpay signature header | raw JSON body, `X-Razorpay-Signature` | dict | `Payment`, `Booking` | Processes captured/refund events | 400/500 signature config, JSON errors possible | High |

## Image/upload endpoints

| Method | Path | Router/file | Auth | Request | Response | Models touched | Side effects | Visible errors | Priority |
|---|---|---|---|---|---|---|---|---|---|
| POST | `/api/v1/shops/{shop_id}/image` | `app/api/v1/shops.py::upload_shop_image` | Bearer shop owner | multipart `file` | `ShopOut` | `Shop`, `ShopImage` | Uploads to Cloudinary, replaces/creates shop image | 400 type/size, 403 not owner, 404 shop | High |
| POST | `/api/v1/bikes/{bike_id}/images` | `app/api/v1/listing.py::upload_bike_images` | Bearer shop owner | multipart `files` list, max 3 total | `BikeOut` | `Bike`, `Shop`, `BikeImage` | Uploads each image to Cloudinary | 400 none/type/size/count, 403 not owner, 404 | High |
| POST | `/api/v1/rentalos/bookings/{booking_id}/documents` | `app/api/v1/rentalos.py::upload_rental_booking_document` | Bearer RentalOS owner/staff | multipart `document_type`, `file` | `RentalBookingDocumentResponse` | `RentalBooking`, `RentalBookingDocument` | Uploads DL/ID proof to Azure Blob, stores metadata | 400 type/size/doc type/empty, 403, 404, 500 Azure config/upload | High |
| POST | `/api/v1/rentalos/bookings/{booking_id}/handover-photo` | `app/api/v1/rentalos.py::upload_rental_handover_photo` | Bearer RentalOS owner/staff | multipart `file`, optional location fields | `RentalHandoverPhotoResponse` | `RentalBooking`, `RentalHandoverPhoto` | Uploads handover photo to Azure Blob, stores metadata | 400 type/size/lat/lng/empty, 403, 404, 500 Azure config/upload | High |

## RentalOS endpoints

All RentalOS endpoints are in `app/api/v1/rentalos.py`, router prefix `/rentalos`, final base path `/api/v1/rentalos`.

| Method | Path | Auth | Request | Response | Models touched | Side effects | Visible errors | Priority |
|---|---|---|---|---|---|---|---|---|
| GET | `/api/v1/rentalos/me` | Bearer user | none | `RentalOSMeResponse` | `User`, `Shop`, `RentalStaff` | None | 401 | High |
| POST | `/api/v1/rentalos/staff` | Bearer shop owner | `RentalStaffCreate` | `RentalStaffResponse` | `Shop`, `User`, `RentalStaff` | Creates new `shop_staff` user if needed; creates active staff membership | 400 invalid role/missing password/owner self-add, 403 non-owner, 404 shop, 409 duplicate/conflict | High |
| GET | `/api/v1/rentalos/staff` | Bearer shop owner | query `shop_id` | `list[RentalStaffResponse]` | `Shop`, `RentalStaff`, `User` | None | 403 non-owner, 404 shop | High |
| PATCH | `/api/v1/rentalos/staff/{staff_id}` | Bearer shop owner | `RentalStaffUpdate` | `RentalStaffResponse` | `RentalStaff`, `User`, `Shop` | Updates staff linked user details and/or active state | 400 invalid role, 403 non-owner, 404 staff/shop | High |
| GET | `/api/v1/rentalos/catalog/vehicles` | Bearer owner or active `RentalStaff` | query `shop_id`, optional `start_time`, `end_time` | `list[CatalogVehicleResponse]` | `Shop`, `RentalStaff`, `Bike`, `BikeImage`, `Booking`, `RentalBooking` | None | 400 partial/invalid time, 403, 404 shop | High |
| GET | `/api/v1/rentalos/customers/search` | Bearer owner/staff | query `shop_id`, `phone` | `RentalCustomerSearchResponse` | `Shop`, `RentalStaff`, `RentalCustomer`, `RentalCustomerFlag`, `RentalBooking`, `RentalBookingNote` | None | 403, 404 shop | High |
| POST | `/api/v1/rentalos/customers` | Bearer owner/staff | `RentalCustomerCreate` | `RentalCustomerOut` | `RentalCustomer`, `Shop`, `RentalStaff` | Creates shop-scoped customer and consent timestamps | 409 duplicate, 403, 404 shop | High |
| POST | `/api/v1/rentalos/bookings` | Bearer owner/staff | `RentalBookingCreate` | `RentalBookingResponse` | `RentalBooking`, `RentalCustomer`, `RentalBookingNote`, `Bike`, `Shop`, `RentalStaff`, `Booking` | Locks bike row, creates/reuses customer, creates confirmed offline booking, optional note | 400 time/bike-shop mismatch, 403, 404, 409 conflict/unavailable | High |
| GET | `/api/v1/rentalos/bookings` | Bearer owner/staff | query `shop_id`, optional `status`, `start_date`, `end_date` | `list[RentalBookingResponse]` | `RentalBooking`, `RentalCustomer`, `Bike`, `Shop`, `RentalStaff` | None | 400 date range, 403, 404 shop | High |
| GET | `/api/v1/rentalos/bookings/{booking_id}` | Bearer owner/staff | path `booking_id` | `RentalBookingResponse` | `RentalBooking`, `RentalCustomer`, `Bike`, `Shop`, `RentalStaff` | None | 403, 404 | High |
| POST | `/api/v1/rentalos/bookings/{booking_id}/documents` | Bearer owner/staff | multipart `document_type`, `file` | `RentalBookingDocumentResponse` | `RentalBooking`, `RentalBookingDocument` | Azure upload, metadata row | 400, 403, 404, 500 | High |
| GET | `/api/v1/rentalos/bookings/{booking_id}/documents` | Bearer owner/staff | path `booking_id` | `list[RentalBookingDocumentResponse]` | `RentalBooking`, `RentalBookingDocument` | None | 403, 404 | High |
| POST | `/api/v1/rentalos/bookings/{booking_id}/handover-photo` | Bearer owner/staff | multipart file/location fields | `RentalHandoverPhotoResponse` | `RentalBooking`, `RentalHandoverPhoto` | Azure upload, metadata row | 400, 403, 404, 500 | High |
| GET | `/api/v1/rentalos/bookings/{booking_id}/handover-photos` | Bearer owner/staff | path `booking_id` | `list[RentalHandoverPhotoResponse]` | `RentalBooking`, `RentalHandoverPhoto` | None | 403, 404 | High |
| POST | `/api/v1/rentalos/bookings/{booking_id}/payments` | Bearer owner/staff | `RentalPaymentCreate` | `RentalPaymentResponse` | `RentalBooking`, `RentalPayment` | Records offline payment; updates booking payment summary fields | 400 invalid/cancelled/completed, 403, 404 | High |
| GET | `/api/v1/rentalos/bookings/{booking_id}/payments` | Bearer owner/staff | path `booking_id` | `list[RentalPaymentResponse]` | `RentalBooking`, `RentalPayment` | None | 403, 404 | High |
| POST | `/api/v1/rentalos/bookings/{booking_id}/complete` | Bearer owner/staff | `RentalBookingCompleteRequest` | `RentalBookingResponse` | `RentalBooking`, `RentalBookingNote`, `RentalCustomer`, `RentalCustomerFlag` | Marks completed, optional note, optional active customer flag/current status | 400 already/cancelled/invalid flag, 403, 404 | High |
| POST | `/api/v1/rentalos/bookings/{booking_id}/notes` | Bearer owner/staff | `RentalBookingNoteCreate` | `RentalBookingNoteResponse` | `RentalBooking`, `RentalBookingNote` | Adds note | 400 empty note, 403, 404 | Medium |
| GET | `/api/v1/rentalos/bookings/{booking_id}/notes` | Bearer owner/staff | path `booking_id` | `list[RentalBookingNoteResponse]` | `RentalBooking`, `RentalBookingNote` | None | 403, 404 | Medium |
| POST | `/api/v1/rentalos/customers/{customer_id}/flags` | Bearer owner/staff | `RentalCustomerFlagCreate` | `RentalCustomerFlagResponse` | `RentalCustomer`, `RentalCustomerFlag` | Adds flag; active flag updates `current_flag_status` | 400 invalid/empty note, 403, 404 | High |
| GET | `/api/v1/rentalos/customers/{customer_id}/flags` | Bearer owner/staff | path `customer_id` | `list[RentalCustomerFlagResponse]` | `RentalCustomer`, `RentalCustomerFlag` | None | 403, 404 | Medium |

## Other routers found

| Method | Path | Router/file | Auth | Request | Response | Models touched | Side effects | Visible errors | Priority |
|---|---|---|---|---|---|---|---|---|---|
| POST | `/api/v1/reviews/{shop_id}` | `app/api/v1/reviews.py::create_review` | Bearer `customer` | `ReviewCreate` | `ReviewOut` | `Booking`, `Bike`, `Review`, `User` | Creates sanitized review after completed/returned booking | 400 duplicate, 403 non-customer/no booking | Medium |
| GET | `/api/v1/reviews/{shop_id}` | `app/api/v1/reviews.py::get_shop_reviews` | Public | path `shop_id`, query `skip`, `limit` | `list[ReviewOut]` | `Review` | None | None explicit | Low |
| PUT | `/api/v1/reviews/{shop_id}/{review_id}` | `app/api/v1/reviews.py::update_review` | Bearer review owner | `ReviewUpdate` | `ReviewOut` | `Review` | Updates sanitized review fields | 403 not owner, 404 | Medium |
| DELETE | `/api/v1/reviews/{shop_id}/{review_id}` | `app/api/v1/reviews.py::delete_review` | Bearer review owner | path ids | 204 | `Review` | Deletes review | 403 not owner, 404 | Medium |
| GET | `/api/v1/statistics/summary` | `app/api/v1/statistics.py::get_stats_summary` | Public | none | `StatsSummaryResponse` | `Shop`, `Bike`, `Booking` | Uses in-memory 48-hour cache | None explicit | Low |
| GET | `/api/v1/statistics/shops` | `app/api/v1/statistics.py::total_shops` | Public | none | `ShopStatsResponse` | `Shop` | None | None explicit | Low |
| GET | `/api/v1/statistics/vehicles` | `app/api/v1/statistics.py::total_vehicles` | Public | none | `VehicleStatsResponse` | `Bike` | None | None explicit | Low |
| GET | `/api/v1/statistics/bookings` | `app/api/v1/statistics.py::total_bookings` | Public | none | `BookingStatsResponse` | `Booking` | None | None explicit | Low |

## Non-versioned app endpoints

| Method | Path | File | Auth | Notes |
|---|---|---|---|---|
| GET | `/` | `app/main.py::read_root` | Public | Metadata |
| GET | `/api` | `app/main.py::api_info` | Public | Metadata |
| GET | `/robots.txt` | `app/main.py::robots_txt` | Public | Not in OpenAPI |
| GET | `/health` | `app/main.py::health_check` | Public | DB `SELECT 1`; raises 503 if unavailable |
| GET | `/ready` | `app/main.py::readiness_probe` | Public | DB `SELECT 1`; raises 503 if unavailable |
