# 🛵 RentWheels API

![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?logo=postgresql)
![Docker](https://img.shields.io/badge/Docker-2CA5E0?logo=docker)

> High-performance FastAPI backend for the RentWheels vehicle rental platform.

RentWheels is a comprehensive platform connecting shop owners with customers looking to rent vehicles. This API powers the entire ecosystem, allowing shop owners to list vehicles, manage inventory, and handle bookings, while enabling customers to browse, search, book, and review their rides.

---

## ✨ Key Features

- **🔐 Robust Security**: JWT-based authentication, bcrypt password hashing, email verification, and scoped shop ownership checks.
- **🛍️ Multi-Tenant Support**: Full support for multiple rental shops, each managing their own unique inventory, bookings, and customer reviews.
- **🔍 Advanced Search**: Search vehicles by type, engine displacement (CC), availability dates, and specific shops.
- **📦 Reliable Inventory Management**: Concurrency-safe inventory tracking using row-level locking to prevent double-bookings and race conditions.
- **📅 Complete Booking Lifecycle**: Manages bookings through a clear state machine: `pending` → `confirmed` → `completed` → `cancelled`.
- **🏪 RentalOS Counter System**: Separate offline rental desk APIs for catalog, customer lookup, offline bookings, Azure document/handover uploads, payment tracking, trip completion, notes, customer flags, and owner-managed staff access.
- **⭐ Verified Reviews**: Prevents spam by ensuring users can only leave reviews after completing a booking.
- **🛡️ Operational Stability**: Built-in rate limiting, input sanitization, structural logging, and health checks for production readiness.

## 🛠️ Tech Stack

- **Framework**: FastAPI (with Pydantic for validation)
- **Database**: PostgreSQL
- **ORM & Migrations**: SQLAlchemy & Alembic
- **Infrastructure**: Docker & Docker Compose

---

## 🚀 Quick Start (Local Development)

### Prerequisites
- Python 3.11+
- PostgreSQL 14+ (or Docker to run it)

### 1. Clone & Install

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

Create a `.env` file in the root directory. You can use the following template:

```env
# Database Configuration
database_hostname=localhost
database_port=5432
database_username=postgres
database_password=your_password
database_name=rentwheels

# Security
secret_key=your-secret-key-minimum-32-characters
algorithm=HS256
access_token_expire_minutes=30

# Environment Details
environment=development
debug=true
cors_origins=http://localhost:3000,http://127.0.0.1:3000

# RentalOS Azure Blob Storage
AZURE_STORAGE_CONNECTION_STRING=
AZURE_STORAGE_RENTALOS_CONTAINER=
AZURE_STORAGE_RENTALOS_MAX_UPLOAD_MB=5
AZURE_STORAGE_RENTALOS_PUBLIC_BASE_URL=
```

### 3. Database Setup & Run

```bash
# Apply database migrations
alembic upgrade head

# Start the development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Your API is now available at:
- **API Base**: `http://localhost:8000`
- **Swagger Docs**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **Health Check**: `http://localhost:8000/health`

---

## 🐳 Running with Docker

The easiest way to get the entire stack (API + Database) running is using Docker Compose.

1. Ensure you have your `.env` file configured.
2. Run the compose stack:

```bash
docker compose up -d --build
```

To build and run the API container manually:

```bash
docker build -t rentwheels-backend .
docker run -d --name rentwheels-backend -p 8000:8000 --env-file ./.env rentwheels-backend
```

---

## 📚 API Surface Overview

The API is versioned at `/api/v1`. All endpoints (except auth and public search) require a valid JWT token.

| Domain | Key Endpoints | Description |
| :--- | :--- | :--- |
| **Auth** | `/login`, `/google` | Token generation |
| **Users** | `/users/` | User registration and management |
| **Shops** | `/shops/` | Shop creation and management |
| **Vehicles**| `/bikes/`, `/search/vehicles/` | Vehicle listings and advanced search |
| **Bookings**| `/bookings/` | Reservation lifecycle management |
| **Inventory**|`/inventory/` | Stock tracking and adjustments |
| **Reviews** | `/reviews/` | Verified customer feedback |
| **RentalOS** | `/rentalos/*` | Offline counter catalog, customer lookup, bookings, uploads, payments, completion, notes, flags, and staff management |
| **System** | `/password-reset/*` | Account recovery |

*For complete endpoint details, request payloads, and response schemas, refer to the automatically generated [Swagger UI](http://localhost:8000/docs) after starting the server.*

## 🏪 RentalOS Notes

RentalOS is separate from the online marketplace flow.

- Staff and owners log in through the normal `POST /api/v1/login` endpoint.
- Frontend should call `GET /api/v1/rentalos/me` after login to decide whether to show owner RentalOS, staff RentalOS, or no RentalOS access.
- Owners are resolved through `Shop.owner_id == current_user.id`.
- Staff are normal `User` rows with active `RentalStaff` membership.
- Staff management endpoints are owner-only: `POST /rentalos/staff`, `GET /rentalos/staff?shop_id=...`, `PATCH /rentalos/staff/{staff_id}`.
- RentalOS documents and handover photos use Azure Blob Storage, not Cloudinary.
- Marketplace bike/shop images still use Cloudinary.
- RentalOS payments use `RentalPayment`; Razorpay marketplace payments use `Payment`.

See [docs/rentalos-frontend-handoff.md](docs/rentalos-frontend-handoff.md) for frontend integration details.

---

## 🧪 Testing

Run the test suite using pytest:

```bash
.venv/bin/pytest
```

---

## 🏗️ Project Structure

```text
backend/
├── app/                 # Main FastAPI application source code
│   ├── main.py          # App entrypoint
│   ├── api/v1/          # Route handlers
│   ├── db/              # SQLAlchemy database setup and models
│   ├── schemas/         # Pydantic validation schemas
│   └── utils/           # Auth, uploads, email, logging, timezone helpers
├── alembic/             # Database migration scripts
├── docs/                # RentalOS/frontend/backend handoff documentation
├── tests/               # Pytest test suite
├── alembic.ini          # Alembic configuration
├── requirements.txt     # Python dependencies
├── Dockerfile           # Container build instructions
└── docker-compose.yml   # Multi-container orchestration
```

---

## 🌍 Production Deployment

When deploying to production, ensure the following steps are taken:

1. **Environment Variables**:
   - Set `environment=production`
   - Set `debug=false` (This disables the Swagger UI docs for security)
   - Ensure `cors_origins` is strictly limited to your frontend domain(s)
   - Use a strong, randomly generated value for `secret_key`
   - Use a managed PostgreSQL instance for reliability and backups
   - Configure a private Azure Blob container for RentalOS document/handover uploads
   - Add signed/authenticated RentalOS file access before exposing sensitive documents in production
2. **Reverse Proxy**: Serve the API behind a reverse proxy like Nginx or Traefik to handle SSL/TLS (HTTPS).
3. **Process Management**: Run the application via `gunicorn` with `uvicorn` workers for optimal performance.
