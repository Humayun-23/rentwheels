# GoPanda Project Overview

Paths in this report are repo-relative from `/Users/humayun/ridewheel/backend`.

## Project Summary

GoPanda is a vehicle rental marketplace backend with a separate RentalOS backend module for offline shop counter operations. The online marketplace flow supports public discovery, customer bookings, Razorpay payment handling, Cloudinary image uploads, inventory, reviews, and owner dashboards. RentalOS supports walk-in rental desk operations without mixing offline bookings/payments with the online marketplace booking/payment models.

## Main Modules

- API entrypoint: `app/main.py`
- Database/session setup: `app/db/database.py`
- SQLAlchemy models: `app/db/models.py`
- API routers: `app/api/v1/*.py`
- Pydantic schemas: `app/schemas/*.py`
- Utilities: `app/utils/*.py`
- Alembic migrations: `alembic/versions/*.py`
- Tests: `tests/*.py`
- RentalOS API: `app/api/v1/rentalos.py`
- RentalOS schemas: `app/schemas/rentalos.py`
- RentalOS Azure utility: `app/utils/rentalos_azure_blob.py`

## Backend Tech Stack

- FastAPI
- SQLAlchemy ORM
- Alembic
- PostgreSQL by default
- PyJWT bearer auth
- SlowAPI rate limiting on selected public/auth endpoints
- Pydantic v2 schemas/settings
- Razorpay HTTP integration for online marketplace payments
- Cloudinary for marketplace bike/shop images
- Azure Blob Storage for RentalOS documents and handover photos
- Pytest with FastAPI `TestClient` and SQLite test overrides

## Frontend Tech Stack Visible From Repo

Visible sibling frontend files:

- `../ride-elegance/package.json`
- `../ride-elegance/vite.config.ts`
- `../ride-elegance/tailwind.config.ts`

Observed frontend stack:

- React 18
- Vite 5
- TypeScript
- Tailwind CSS
- Radix UI / shadcn-style dependencies
- React Router
- TanStack React Query
- Axios
- Vitest

RentalOS frontend status: not started.

## Deployment And Config Status

- `app/config.py` uses `pydantic_settings.BaseSettings` with `.env`.
- `app/db/database.py` builds a PostgreSQL URL from DB settings and appends `sslmode=require`.
- `app/db/database.py` uses `NullPool`, with comments referencing Neon serverless behavior.
- `app/main.py` includes middleware comments referencing Azure load balancer/trusted host behavior.
- `Dockerfile`, `docker-compose.yml`, `nginx.conf`, and `.github/workflows/deploy.yml` exist.
- FastAPI docs are disabled when `settings.environment == "production"`.
- Production deployment/provider is not active for this handoff.
- Production migrations are not applied.
- Azure RentalOS container privacy is not in place yet.
- Signed/authenticated RentalOS file access is not implemented yet.

## Existing Marketplace Capabilities

- User registration, email verification, resend verification, password reset.
- Login with email/password and Google credential login.
- Shop CRUD for shop owners.
- Shop dashboard metrics and analytics.
- Public shop listing/detail.
- Vehicle CRUD for shop-owned vehicles.
- Vehicle search and type search.
- Inventory tracking by bike.
- Online booking create/list/detail/update/cancel/confirm/reject/complete/return.
- Magic-link reject action for bookings.
- Razorpay payment order creation, verification, cancellation, refund, and webhook.
- Bike and shop image uploads through Cloudinary.
- Reviews for shops after completed/returned bookings.
- Public statistics endpoints.

## RentalOS Capabilities

- Shop-scoped catalog with availability status.
- Shop-scoped customer phone lookup.
- Offline rental customer creation with document/marketing consent fields.
- Offline booking create/list/detail.
- Conflict checks against online `Booking` and offline `RentalBooking`.
- Azure Blob upload/list for booking documents.
- Azure Blob upload/list for handover photos with optional location metadata.
- Offline payment recording/list using `RentalPayment`.
- Trip completion.
- Booking notes.
- Customer flags.
- `/api/v1/rentalos/me` for frontend access discovery.
- Owner-only staff create/list/update/deactivate.
- Owner or active `RentalStaff` access for counter APIs.

## Implemented Vs Not Implemented

Implemented:

- Backend routes listed in `docs/agent-handoff/api-endpoints-report.md`.
- RentalOS database models and migration foundation.
- RentalOS core APIs, upload APIs, payment recording, completion, notes, flags, current-user access, and staff management.
- Marketplace Razorpay and Cloudinary flows.

Not implemented:

- RentalOS frontend.
- Separate RentalOS staff login.
- RentalOS signed URL or authenticated file download flow.
- Staff invitation email flow.
- Staff hard-delete.
- Dynamic RBAC/permission tables.
- RentalOS analytics.
- RentalOS invoices.
- RentalOS SMS/email/WhatsApp automation.
- Native app.
- OCR or sensitive number extraction/storage.
- Full shared availability service used by both marketplace and RentalOS booking creation.

## Important Risks And Unknowns

- RentalOS document/photo responses store and return blob URLs in `file_url`/`image_url`; signed/authenticated file access is still needed before production.
- RentalOS and marketplace conflict logic are not centralized. `app/api/v1/rentalos.py` has a TODO that online booking creation should use the same shared lock/availability service later.
- Online `pending`, `paid`, and `confirmed` bookings block RentalOS availability.
- Existing marketplace booking inventory counters and time-window conflict logic need regression protection when availability logic is centralized later.
- `ridewheel.db` is deleted in current worktree status; this appears unrelated to RentalOS docs/code and should not be restored without owner direction.
- `app/db/database.py` has an existing modified `NullPool` change; do not assume it is part of a docs-only task.

## Current Test Status

Fresh full test run after PR5:

```text
.venv/bin/pytest
36 passed
```
