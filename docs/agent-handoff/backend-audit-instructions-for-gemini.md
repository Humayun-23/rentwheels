# Backend Audit Instructions For Gemini

You are auditing the GoPanda backend.

Use the reports in `docs/agent-handoff/` and the actual backend code. Do not assume features that are not present in code. If there is uncertainty, mark it as `Needs verification`.

## Primary goals

- Write tests first for high-risk backend areas.
- Focus on access control, booking conflicts, payment separation, file upload validation, and RentalOS/marketplace separation.
- Preserve existing behavior.
- Do not rewrite architecture unless a test-proven bug requires a small fix.
- Produce small focused PRs.
- Report risks clearly with exact file paths, functions, classes, and endpoint names.

## Product boundaries

GoPanda has an existing online marketplace flow and a separate RentalOS offline counter flow.

Keep these separate:

- Online marketplace bookings use `Booking`.
- RentalOS offline bookings use `RentalBooking`.
- Online marketplace payments use Razorpay and `Payment`.
- RentalOS offline payments use `RentalPayment`.
- Marketplace bike/shop images use Cloudinary.
- RentalOS documents/handover photos use Azure Blob Storage.

Do not add:

- Frontend.
- RentalOS staff management unless explicitly requested later.
- Analytics.
- Invoices.
- SMS/email automation.
- OCR.
- Native app.
- Complex RBAC.
- Architecture rewrites.

## Recommended task order

1. Read all `docs/agent-handoff/` reports.
2. Inspect actual backend code.
3. Run existing tests.
4. Confirm failing tests and classify whether unrelated.
5. Add or repair test fixtures.
6. Write RentalOS access tests.
7. Write booking conflict tests.
8. Write upload validation tests.
9. Write payment/trip completion tests.
10. Write marketplace regression tests.
11. Produce backend audit findings.
12. Suggest small fixes only after tests reveal issues.

## Files to inspect first

- `app/main.py`
- `app/config.py`
- `app/db/database.py`
- `app/db/models.py`
- `app/api/v1/oauth2.py`
- `app/api/v1/auth.py`
- `app/api/v1/booking.py`
- `app/api/v1/payments.py`
- `app/api/v1/listing.py`
- `app/api/v1/shops.py`
- `app/api/v1/rentalos.py`
- `app/schemas/rentalos.py`
- `app/utils/rentalos_azure_blob.py`
- `tests/conftest.py`

## High-risk areas

- Cross-shop data isolation.
- Owner versus active RentalStaff RentalOS access.
- Inactive staff access.
- RentalOS booking conflict logic across online `Booking` and offline `RentalBooking`.
- Online booking conflict logic still working after RentalOS changes.
- Direct blob URL exposure for sensitive RentalOS files.
- File content type/size validation.
- RentalOS payment summary updates.
- Separation of `Payment` and `RentalPayment`.
- Separation of Cloudinary marketplace uploads and Azure RentalOS uploads.
- Rate limiter impact on tests.

## Expected conflict behavior to verify

- Online pending `Booking` blocks RentalOS booking.
- Online confirmed `Booking` blocks RentalOS booking.
- Online paid `Booking` blocks RentalOS booking.
- Online completed `Booking` does not block RentalOS booking.
- RentalBooking draft/confirmed/active blocks.
- RentalBooking completed/cancelled does not block.
- Non-overlapping booking succeeds.
- Back-to-back booking succeeds.

Known mismatch to test:

- Product decision: online paid `Booking` should block RentalOS.
- Current RentalOS code checks online pending/confirmed only, so write a failing test before suggesting a small fix.

## Expected upload behavior to verify

Documents:

- Allowed: JPEG, PNG, WebP, PDF.
- Allowed document types: `driving_license`, `id_proof`.
- Oversized files rejected.
- Empty files rejected.
- Other shops cannot view/upload.
- Stored blob path must not trust original filename.

Handover photos:

- Allowed: JPEG, PNG, WebP.
- PDF rejected.
- Latitude must be `-90..90`.
- Longitude must be `-180..180`.
- Location is optional.
- `location_permission_granted=false` does not require lat/lng.

## Expected payment behavior to verify

- RentalOS advance increases `RentalBooking.advance_paid`.
- RentalOS balance reduces `RentalBooking.balance_due`, not below 0.
- RentalOS security deposit increases `RentalBooking.security_deposit`.
- RentalOS refund reduces `RentalBooking.security_deposit`, not below 0.
- RentalOS extra charge increases `RentalBooking.total_amount` if present.
- Cancelled/completed RentalOS bookings reject new payments.
- RentalOS payments create `RentalPayment`, not `Payment`.
- Razorpay flow still creates/updates `Payment`, not `RentalPayment`.

## Reporting format

For audit findings:

- Start with bugs/risks ordered by severity.
- Include exact file path and function/class/endpoint.
- Include why it matters.
- Include a minimal suggested fix.
- Mark uncertain items as `Needs verification`.

For PRs:

- Keep changes small.
- Do not refactor unrelated files.
- Do not change marketplace behavior unless a regression test proves a bug and the fix is explicitly scoped.
