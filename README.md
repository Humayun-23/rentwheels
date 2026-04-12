# RentWheels API

FastAPI backend for a vehicle rental platform. Shop owners list vehicles, customers browse and book, and both sides manage the booking lifecycle.

## Highlights

- JWT authentication with role-based access (customer, shop owner, admin)
- Multi-shop support with inventory, bookings, and reviews
- Search with filters (type, engine CC, availability, shop)
- Rate limiting for sensitive endpoints
- Input sanitization for user-generated content
- PostgreSQL + SQLAlchemy + Alembic migrations

## Feature overview

- **Auth & security**: JWT tokens, bcrypt hashing, admin token + IP allowlist
- **Booking lifecycle**: pending → confirmed → completed → cancelled
- **Inventory**: tracked quantities with row-level locking to prevent race conditions
- **Reviews**: only after completed bookings, prevents duplicates
- **Search**: by vehicle type, engine CC, availability, and shop
- **Pagination**: all list endpoints support `skip`/`limit`
- **Ops**: health check endpoint and structured logging

## Tech stack

- FastAPI, Pydantic, SQLAlchemy, Alembic
- PostgreSQL
- Docker and Docker Compose

## Requirements

- Python 3.11+
- PostgreSQL 14+

## Quick start (local)

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a .env in this folder:

```env
database_hostname=localhost
database_port=5432
database_username=postgres
database_password=your_password
database_name=rentwheels
secret_key=your-secret-key-minimum-32-characters
algorithm=HS256
access_token_expire_minutes=30
admin_token=your-admin-token
admin_allowed_hosts=127.0.0.1,::1
environment=development
debug=true
cors_origins=http://localhost:3000,http://127.0.0.1:3000
```

Run migrations and start the server:

```bash
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Endpoints:

- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

User creation requires `firstname` and `lastname`:

```bash
curl -X POST "http://localhost:8000/api/v1/users/" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "SecurePass123",
    "firstname": "John",
    "lastname": "Doe",
    "phone_number": "1234567890",
    "user_type": "customer"
  }'
```

## API surface (high level)

- `/api/v1/login`, `/api/v1/admin/login`
- `/api/v1/users`, `/api/v1/shops`, `/api/v1/bikes`
- `/api/v1/bookings`, `/api/v1/inventory`, `/api/v1/reviews`
- `/api/v1/search/vehicles`
- `/api/v1/password-reset/request`, `/api/v1/password-reset/confirm`

## Docker

Build and run:

```bash
docker build -t rentwheels-backend .
docker run -d --name rentwheels-backend -p 8000:8000 \
  --env-file ./.env rentwheels-backend
```

## Docker Compose

Place docker-compose.yml and .env in this folder, then:

```bash
docker compose up -d --build
```

## Deployment (overview)

- Build and run with Docker or Docker Compose
- Load environment variables via `.env`
- Serve HTTPS via a reverse proxy (e.g., Nginx + Let's Encrypt)
- Add CI/CD to build and deploy on push
- Open required ports (80/443 for HTTPS, 8000 if exposing directly)

## Project structure

```
backend/
  app/                 # FastAPI app
  alembic/             # Migrations
  scripts/             # Seed scripts
  requirements.txt
  alembic.ini
  Dockerfile
  docker-compose.yml
```

## Development

```bash
pytest
```

## Production notes

- Set environment=production and debug=false in .env
- Configure allowed CORS origins in cors_origins
- Docs are disabled in production