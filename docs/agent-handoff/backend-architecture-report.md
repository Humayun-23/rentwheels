# Backend Architecture Report

Paths in this report are repo-relative from `/Users/humayun/ridewheel/backend`.

## Folder structure

- `app/main.py`: FastAPI app construction, middleware, router registration, root/health/readiness routes.
- `app/api/v1/`: API routers.
- `app/db/database.py`: SQLAlchemy engine/session/base setup.
- `app/db/models.py`: all SQLAlchemy ORM models.
- `app/schemas/`: Pydantic request/response schemas.
- `app/utils/`: shared utilities for auth hashing, email, logging, rate limiting, Cloudinary, Azure Blob, timezone, sanitization.
- `alembic/`: migrations.
- `tests/`: pytest tests with FastAPI `TestClient`.
- `requirements.txt`: Python dependencies.

## Main app entrypoint

File: `app/main.py`

Main object:

- `app = FastAPI(...)`

Main middleware:

- `LoggingMiddleware` from `app/utils/logging_config.py`
- `TrustedHostMiddleware`
- SlowAPI exception handler for `RateLimitExceeded`
- `CORSMiddleware`
- `GZipMiddleware`

Main non-router endpoints:

- `GET /`
- `GET /api`
- `GET /robots.txt`
- `GET /health`
- `GET /ready`

Startup/shutdown:

- `startup_event()` checks DB connection with `SELECT 1`.
- `shutdown_event()` calls `dispose_engine()`.

## Router registration structure

All versioned routers are included in `app/main.py` with prefix `/api/v1`:

- `auth.router`
- `users.router`
- `shops.router`
- `booking.router`
- `listing.router`
- `inventory.router`
- `searchvehicle.router`
- `reviews.router`
- `passwordreset.router`
- `payments.router`
- `statistics.router`
- `rentalos.router`

RentalOS registration:

- Include prefix in `app/main.py`: `/api/v1`
- Router prefix in `app/api/v1/rentalos.py`: `/rentalos`
- Final base path: `/api/v1/rentalos`
- No duplicate `/rentalos/rentalos` prefix observed.

## Config/settings pattern

File: `app/config.py`

Class:

- `Settings(BaseSettings)`

Pattern:

- Reads `.env`.
- Ignores extra env vars.
- Uses validation aliases for uppercase env names where needed.
- `settings = Settings()` is imported by app modules.

Important settings:

- Database settings: `database_hostname`, `database_port`, `database_password`, `database_name`, `database_username`
- JWT settings: `secret_key`, `algorithm`, `access_token_expire_minutes`
- CORS/debug: `cors_origins`, `environment`, `debug`
- Marketplace image config: `cloudinary_url`
- RentalOS Azure config:
  - `azure_storage_connection_string`
  - `azure_storage_rentalos_container`
  - `azure_storage_rentalos_max_upload_mb`
  - `azure_storage_rentalos_public_base_url`

Confirmed code behavior:

- Razorpay and SMTP env values are read directly through `os.getenv()` in router/helper files, not centralized in `Settings`.

## Database/session setup

File: `app/db/database.py`

Objects/functions:

- `DATABASE_URL`
- `engine = create_engine(...)`
- `SessionLocal = sessionmaker(...)`
- `Base = declarative_base()`
- `get_db()`
- `dispose_engine()`
- `set_cache_headers()`

Observed behavior:

- PostgreSQL URL is built from settings and `sslmode=require`.
- `NullPool` is used.
- `get_db()` yields a session and closes it in `finally`.
- Tests override `get_db()` in `tests/conftest.py` to use in-memory SQLite with `StaticPool`.

## Auth dependency flow

Files:

- `app/api/v1/auth.py`
- `app/api/v1/oauth2.py`
- `app/utils/utils.py`

Flow:

1. `POST /api/v1/login` receives `OAuth2PasswordRequestForm`.
2. `login()` finds `User` by email, verifies password with `verify_password()`, requires `is_email_verified`.
3. `create_access_token()` encodes JWT with `user_id`, `role`, and `exp`.
4. Protected endpoints use `current_user: User = Depends(get_current_user)`.
5. `get_current_user()` decodes bearer token, rejects non-user token roles, loads `User` by ID.

## Utility modules

- `app/utils/utils.py`: password hashing/verification.
- `app/utils/tz.py`: timezone helpers used for datetime defaults and comparisons.
- `app/utils/limiter.py`: SlowAPI limiter.
- `app/utils/logging_config.py`: logging middleware/config.
- `app/utils/cloudinary_client.py`: existing Cloudinary uploads for marketplace bike/shop images.
- `app/utils/rentalos_azure_blob.py`: isolated RentalOS Azure Blob upload/validation utility.
- `app/utils/email.py` and `app/utils/mail.py`: email helpers.
- `app/utils/sanitization.py`: review comment sanitization.
- `app/utils/performance.py`: present; detailed use Needs verification.

## External service integrations

Marketplace:

- Razorpay in `app/api/v1/payments.py`.
- Cloudinary in `app/utils/cloudinary_client.py`, called by `app/api/v1/listing.py` and `app/api/v1/shops.py`.
- Google ID token verification in `app/api/v1/auth.py`.
- SMTP email in `app/api/v1/users.py`, `app/api/v1/passwordreset.py`, and `app/api/v1/booking.py`.

RentalOS:

- Azure Blob Storage in `app/utils/rentalos_azure_blob.py`, called only by `app/api/v1/rentalos.py`.

## Backend conventions observed

- Routers are mounted under `/api/v1`.
- Most owner checks use `Shop.owner_id == current_user.id`.
- Customer-only actions check `current_user.user_type == "customer"`.
- Shop-owner actions check `current_user.user_type == "shop_owner"`.
- RentalOS access allows either `Shop.owner_id == current_user.id` or active `RentalStaff`.
- Pydantic v2 `model_dump()` and `ConfigDict(from_attributes=True)` are used.
- SQLAlchemy relationships use `cascade="all, delete-orphan"` for owned child collections.
- File upload validation checks content type and size before storage.

## Architectural concerns noticed

- Booking availability logic is duplicated between marketplace booking and RentalOS booking.
- Online `Booking` creation updates `BikeInventory` counters, but RentalOS bookings do not touch inventory counters and rely on conflict windows/statuses.
- RentalOS sensitive file metadata returns blob URLs directly. Signed/authenticated RentalOS file access is not implemented yet.
- Some env vars are centralized in `Settings`; others are read directly with `os.getenv()`.
- Rate limiting currently affects tests: `.venv/bin/pytest` fails two `tests/test_users.py` cases because `/api/v1/login` returns SlowAPI 429 for `testclient`.
- Existing dashboard analytics endpoints are in the marketplace backend; keep them separate from RentalOS analytics, which are not implemented.
