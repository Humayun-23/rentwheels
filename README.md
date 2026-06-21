# 🛵 RentWheels API

![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?logo=postgresql)
![Docker](https://img.shields.io/badge/Docker-2CA5E0?logo=docker)

> High-performance FastAPI backend for the RentWheels vehicle rental platform.

RentWheels is a comprehensive platform connecting shop owners with customers looking to rent vehicles. This API powers the entire ecosystem, allowing shop owners to list vehicles, manage inventory, and handle bookings, while enabling customers to browse, search, book, and review their rides.

---

## ✨ Key Features

- **🔐 Robust Security**: JWT-based authentication with role-based access control (Admin, Shop Owner, Customer), bcrypt password hashing, and admin IP allowlisting.
- **🛍️ Multi-Tenant Support**: Full support for multiple rental shops, each managing their own unique inventory, bookings, and customer reviews.
- **🔍 Advanced Search**: Search vehicles by type, engine displacement (CC), availability dates, and specific shops.
- **📦 Reliable Inventory Management**: Concurrency-safe inventory tracking using row-level locking to prevent double-bookings and race conditions.
- **📅 Complete Booking Lifecycle**: Manages bookings through a clear state machine: `pending` → `confirmed` → `completed` → `cancelled`.
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

# Admin Access
admin_token=your-admin-token
admin_allowed_hosts=127.0.0.1,::1

# Environment Details
environment=development
debug=true
cors_origins=http://localhost:3000,http://127.0.0.1:3000
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
| **Auth** | `/login`, `/admin/login` | Token generation |
| **Users** | `/users/` | User registration and management |
| **Shops** | `/shops/` | Shop creation and management |
| **Vehicles**| `/bikes/`, `/search/vehicles/` | Vehicle listings and advanced search |
| **Bookings**| `/bookings/` | Reservation lifecycle management |
| **Inventory**|`/inventory/` | Stock tracking and adjustments |
| **Reviews** | `/reviews/` | Verified customer feedback |
| **System** | `/password-reset/*` | Account recovery |

*For complete endpoint details, request payloads, and response schemas, refer to the automatically generated [Swagger UI](http://localhost:8000/docs) after starting the server.*

---

## 🧪 Testing

Run the test suite using pytest:

```bash
pytest
```

---

## 🏗️ Project Structure

```text
backend/
├── app/                 # Main FastAPI application source code
│   ├── main.py          # App entrypoint
│   ├── api/             # Route handlers
│   ├── core/            # Config, security, database sessions
│   ├── models/          # SQLAlchemy database models
│   ├── schemas/         # Pydantic validation schemas
│   └── services/        # Business logic
├── alembic/             # Database migration scripts
├── scripts/             # Utility and database seeding scripts
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
   - Use strong, randomly generated secrets for `secret_key` and `admin_token`
   - Use a managed PostgreSQL instance for reliability and backups
2. **Reverse Proxy**: Serve the API behind a reverse proxy like Nginx or Traefik to handle SSL/TLS (HTTPS).
3. **Process Management**: Run the application via `gunicorn` with `uvicorn` workers for optimal performance.