# RentWheels API 🚴

A production-ready FastAPI backend for a vehicle rental platform. Shop owners can list their vehicles (bikes, scooters, cars) and customers can browse and book them.

## ✨ Features

- 🔐 **JWT Authentication** - Secure token-based auth for customers and shop owners
- 👥 **Role-Based Access Control** - Customer and shop owner roles with different permissions
- 🏪 **Multi-Shop Support** - Shop owners can manage multiple rental shops
- 🚗 **Vehicle Management** - Support for bikes, scooters, and cars
- 📦 **Real-Time Inventory** - Track available and rented quantities with row-level locking
- 📅 **Booking System** - Complete booking lifecycle (pending → confirmed → completed)
- ⭐ **Review System** - Customers can review shops after completing bookings
- 🔍 **Advanced Search** - Search by vehicle type, engine CC, shop, availability
- 🔒 **Password Reset** - Secure token-based password reset flow
- 📊 **Pagination** - All list endpoints support pagination (max 100 per request)
- ⚡ **Rate Limiting** - Protection against abuse on sensitive endpoints
- 🛡️ **Input Sanitization** - XSS prevention with HTML sanitization
- 👨‍💼 **Admin API** - Protected admin endpoints for system management

---

## 📦 Project Structure

```
rentwheels/
├── app/
│   ├── main.py                 # FastAPI app, CORS, rate limiting
│   ├── config.py               # Pydantic settings from .env
│   ├── requirements.txt        # Python dependencies
│   ├── api/v1/
│   │   ├── auth.py            # Login endpoints (user & admin)
│   │   ├── oauth2.py          # JWT & OAuth2 utilities
│   │   ├── users.py           # User CRUD
│   │   ├── shops.py           # Shop CRUD
│   │   ├── listing.py         # Bike/Vehicle CRUD
│   │   ├── booking.py         # Booking lifecycle management
│   │   ├── inventory.py       # Inventory tracking
│   │   ├── reviews.py         # Review system
│   │   ├── searchvehicle.py   # Advanced search
│   │   └── passwordreset.py   # Password reset flow
│   ├── db/
│   │   ├── database.py        # SQLAlchemy engine with connection pooling
│   │   └── models.py          # ORM models
│   ├── schemas/               # Pydantic schemas for validation
│   │   ├── users.py
│   │   ├── shops.py
│   │   ├── bikes.py
│   │   ├── booking.py
│   │   ├── inventory.py
│   │   ├── reviews.py
│   │   ├── password_reset.py
│   │   ├── admin.py
│   │   └── token.py
│   └── utils/
│       ├── utils.py           # Password hashing (bcrypt)
│       ├── sanitization.py    # HTML sanitization (XSS prevention)
│       ├── limiter.py         # Rate limiter instance
│       └── logging_config.py  # Structured logging setup
├── alembic/                   # Database migrations
│   ├── versions/              # Migration files
│   └── env.py
├── scripts/
│   └── seed.py                # Database seeding script
├── .env                       # Environment variables (gitignored)
├── .gitignore
├── alembic.ini                # Alembic configuration
├── PASSWORD_RESET_USAGE.md    # Password reset documentation
└── README.md
```

---

## � Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 14+

### 1. Clone & Install
```bash
git clone https://github.com/Humayun-23/rentwheels.git
cd rentwheels
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r app/requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your settings
```

**Required Environment Variables:**
```env
DATABASE_HOSTNAME=localhost
DATABASE_PORT=5432
DATABASE_USERNAME=postgres
DATABASE_PASSWORD=your_password
DATABASE_NAME=rentwheels
SECRET_KEY=your-secret-key-minimum-32-characters
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ADMIN_TOKEN=your-admin-token-for-protected-endpoints
ADMIN_ALLOWED_HOSTS=127.0.0.1,::1
ENVIRONMENT=development
```

### 3. Setup Database
```bash
# Create database
createdb rentwheels

# Run migrations
alembic upgrade head

# (Optional) Seed sample data
python scripts/seed.py
```

### 4. Run Server
```bash
cd rentwheels
uvicorn app.main:app --reload --port 8000
```

**API Endpoints:**
- API: `http://localhost:8000`
- Interactive Docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Health Check: `http://localhost:8000/health`

---

## 🔐 API Endpoints

### Authentication (`/api/v1`)
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/login` | User login (JWT token) | ❌ |
| POST | `/admin/login` | Admin login | ❌ |

**Rate Limit:** 5 requests/minute per IP

### Password Reset (`/api/v1/password-reset`)
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/request` | Request password reset token | ❌ |
| POST | `/confirm` | Reset password with token | ❌ |

### Users (`/api/v1/users`)
| Method | Endpoint | Description | Auth Required | Pagination |
|--------|----------|-------------|---------------|------------|
| POST | `/` | Create new user | ❌ | - |
| GET | `/{user_id}` | Get user by ID | ❌ | - |
| PUT | `/{user_id}` | Update user | ✅ | - |
| GET | `/` | Get all users (admin only) | ✅ Admin | ✅ |

### Shops (`/api/v1/shops`)
| Method | Endpoint | Description | Auth Required | Pagination |
|--------|----------|-------------|---------------|------------|
| POST | `/` | Create shop | ✅ Shop Owner | - |
| GET | `/{shop_id}` | Get shop details | ❌ | - |
| GET | `/` | Get all shops | ❌ | ✅ |
| PUT | `/{shop_id}` | Update shop | ✅ Owner | - |
| DELETE | `/{shop_id}` | Delete shop | ✅ Owner | - |

### Reviews (`/api/v1/shops/{shop_id}/reviews`)
| Method | Endpoint | Description | Auth Required | Pagination |
|--------|----------|-------------|---------------|------------|
| POST | `/{shop_id}/reviews` | Create review | ✅ Customer | - |
| GET | `/{shop_id}/reviews` | Get shop reviews | ❌ | ✅ |
| PUT | `/{shop_id}/reviews/{review_id}` | Update review | ✅ Owner | - |
| DELETE | `/{shop_id}/reviews/{review_id}` | Delete review | ✅ Owner | - |

**Note:** Customers can only review shops where they've completed bookings. Duplicate reviews prevented.

### Bikes (`/api/v1/bikes`)
| Method | Endpoint | Description | Auth Required | Pagination |
|--------|----------|-------------|---------------|------------|
| POST | `/` | Add bike to shop | ✅ Shop Owner | - |
| GET | `/{bike_id}` | Get bike details | ❌ | - |
| GET | `/shop/{shop_id}` | Get bikes in shop | ❌ | ✅ |
| PUT | `/{bike_id}` | Update bike | ✅ Owner | - |
| DELETE | `/{bike_id}` | Delete bike | ✅ Owner | - |

### Inventory (`/api/v1/inventory`)
| Method | Endpoint | Description | Auth Required | Pagination |
|--------|----------|-------------|---------------|------------|
| POST | `/` | Create inventory | ✅ Shop Owner | - |
| GET | `/bike/{bike_id}` | Get bike inventory | ❌ | - |
| GET | `/shop/{shop_id}` | Get shop inventory | ❌ | ✅ |
| GET | `/available/{bike_id}` | Check availability | ❌ | - |
| PUT | `/{bike_id}` | Update inventory | ✅ Owner | - |
| GET | `/availability/timerange` | Check time range availability | ❌ | - |

### Bookings (`/api/v1/bookings`)
| Method | Endpoint | Description | Auth Required | Pagination |
|--------|----------|-------------|---------------|------------|
| POST | `/` | Create booking | ✅ Customer | - |
| GET | `/{booking_id}` | Get booking details | ✅ Customer | - |
| GET | `/user/` | Get user's bookings | ✅ | ✅ |
| PUT | `/{booking_id}` | Update booking | ✅ Owner | - |
| DELETE | `/{booking_id}` | Cancel booking | ✅ Owner | - |
| POST | `/{booking_id}/confirm` | Confirm booking | ✅ Shop Owner | - |
| POST | `/{booking_id}/reject` | Reject booking | ✅ Shop Owner | - |
| POST | `/{booking_id}/complete` | Complete booking | ✅ Shop Owner | - |

**Rate Limit:** 5 requests/minute per IP on booking creation

**Booking Lifecycle:**
1. Customer creates booking → Status: `pending`
2. Shop owner confirms → Status: `confirmed` (sets `confirmed_at`)
3. Shop owner completes → Status: `completed` (sets `completed_at`, returns inventory)
4. Shop owner/customer can reject/cancel → Status: `cancelled` (returns inventory)

### Search (`/api/v1/search`)
| Method | Endpoint | Description | Pagination |
|--------|----------|-------------|------------|
| GET | `/vehicles` | Search vehicles (filters: type, CC, availability, shop) | ✅ |
| GET | `/vehicles/type/{type}` | Search by vehicle type (scooty/bike/car) | ✅ |

**Search Filters:**
- `vehicle_type`: scooty, bike, car
- `engine_cc`: Exact CC (e.g., 150, 250, 500)
- `cc_min`, `cc_max`: CC range
- `is_available`: true/false
- `shop_id`: Filter by shop

---

## 📊 Database Models

### User
```python
- id: Integer (PK)
- email: String (unique, indexed)
- password: String (bcrypt hashed)
- phone_number: String
- user_type: String ("customer" | "shop_owner")
- created_at, updated_at: DateTime
```

### Shop
```python
- id: Integer (PK)
- name, description, address, city, state, zip_code: String
- owner_id: Integer (FK → User)
- phone_number: String
- opening_time, closing_time: Time
- is_active: Boolean
- created_at, updated_at: DateTime
```

### Bike
```python
- id: Integer (PK)
- shop_id: Integer (FK → Shop, cascade delete)
- name, model, bike_type, description: String
- engine_cc: Integer (for bikes/cars)
- price_per_hour, price_per_day: Integer (cents)
- condition: String ("excellent" | "good" | "fair")
- is_available: Boolean
- created_at, updated_at: DateTime
```

### BikeInventory
```python
- id: Integer (PK)
- bike_id: Integer (FK → Bike, cascade delete)
- shop_id: Integer (FK → Shop, cascade delete)
- total_quantity: Integer
- available_quantity: Integer
- rented_quantity: Integer
- created_at, updated_at: DateTime
```

### Booking
```python
- id: Integer (PK)
- customer_id: Integer (FK → User, cascade delete)
- bike_id: Integer (FK → Bike, cascade delete)
- start_time, end_time: DateTime
- status: String ("pending" | "confirmed" | "completed" | "cancelled")
- total_price: Integer (cents)
- confirmed_at, completed_at: DateTime (nullable)
- created_at, updated_at: DateTime
```

### Review
```python
- id: Integer (PK)
- customer_id: Integer (FK → User, cascade delete)
- shop_id: Integer (FK → Shop, cascade delete)
- rating: Integer (1-5)
- comment: String (HTML sanitized)
- created_at, updated_at: DateTime
```

### PasswordResetToken
```python
- id: Integer (PK)
- user_id: Integer (FK → User, cascade delete)
- token: String (unique, URL-safe, 32 bytes)
- expires_at: DateTime (1 hour expiry)
- is_used: Boolean
- created_at: DateTime
```

### AdminUser
```python
- id: Integer (PK)
- email: String (unique, indexed)
- password: String (bcrypt hashed)
- created_at, updated_at: DateTime
```

---

## � Security Features

### Authentication & Authorization
- ✅ JWT tokens with configurable expiry
- ✅ Bcrypt password hashing (handles >72 char passwords)
- ✅ OAuth2 password flow
- ✅ Role-based access control (customer/shop_owner)
- ✅ Admin token authentication with IP whitelisting

### Data Protection
- ✅ HTML sanitization for user input (reviews)
- ✅ Input validation with Pydantic
- ✅ SQL injection protection (SQLAlchemy ORM)
- ✅ CORS configuration (restricted to specific domains)

### Rate Limiting
- ✅ Login endpoints: 5 requests/minute per IP
- ✅ Booking creation: 5 requests/minute per IP
- ✅ Configurable via slowapi

### Database Security
- ✅ Connection pooling (pool_size=20, pre_ping enabled)
- ✅ Row-level locking for inventory (prevents race conditions)
- ✅ Cascade deletes for referential integrity
- ✅ Indexed foreign keys for performance

---

## 📖 Pagination

All list endpoints support pagination with these query parameters:

**Parameters:**
- `skip`: Number of records to skip (default: 0, min: 0)
- `limit`: Maximum records to return (default: 50, min: 1, max: 100)

**Example:**
```bash
# Get first 50 shops
GET /api/v1/shops?skip=0&limit=50

# Get next 50 shops
GET /api/v1/shops?skip=50&limit=50

# Get first 20 reviews
GET /api/v1/shops/1/reviews?skip=0&limit=20
```

---

## 🧪 Sample API Calls

### 1. Register User
```bash
curl -X POST "http://localhost:8000/api/v1/users/" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "SecurePass123",
    "phone_number": "1234567890",
    "user_type": "customer"
  }'
```

### 2. Login
```bash
curl -X POST "http://localhost:8000/api/v1/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=john@example.com&password=SecurePass123"
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 3. Create Shop (as shop owner)
```bash
curl -X POST "http://localhost:8000/api/v1/shops/" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "City Bikes",
    "description": "Best bikes in town",
    "phone_number": "9876543210",
    "address": "123 Main St",
    "city": "New York",
    "state": "NY",
    "zip_code": "10001",
    "opening_time": "09:00:00",
    "closing_time": "18:00:00"
  }'
```

### 4. Add Bike to Shop
```bash
curl -X POST "http://localhost:8000/api/v1/bikes/" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "shop_id": 1,
    "name": "Honda CB350",
    "model": "CB350",
    "bike_type": "bike",
    "engine_cc": 350,
    "description": "Classic motorcycle",
    "price_per_hour": 500,
    "price_per_day": 3000,
    "condition": "excellent"
  }'
```

### 5. Create Booking
```bash
curl -X POST "http://localhost:8000/api/v1/bookings/" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "bike_id": 1,
    "start_time": "2025-11-10T10:00:00",
    "end_time": "2025-11-10T18:00:00"
  }'
```

### 6. Search Vehicles
```bash
# Search for bikes with 150cc engine
curl "http://localhost:8000/api/v1/search/vehicles?vehicle_type=bike&engine_cc=150"

# Search for available scooters
curl "http://localhost:8000/api/v1/search/vehicles?vehicle_type=scooty&is_available=true"

# Search in specific shop
curl "http://localhost:8000/api/v1/search/vehicles?shop_id=1&skip=0&limit=20"
```

### 7. Password Reset
```bash
# Request reset
curl -X POST "http://localhost:8000/api/v1/password-reset/request" \
  -H "Content-Type: application/json" \
  -d '{"email": "john@example.com"}'

# Reset with token
curl -X POST "http://localhost:8000/api/v1/password-reset/confirm" \
  -H "Content-Type: application/json" \
  -d '{
    "token": "TOKEN_FROM_EMAIL",
    "new_password": "NewSecurePass456"
  }'
```

---

## 🛠️ Development

### Running Tests
```bash
pytest
```

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Code Formatting
```bash
# Format code
black app/

# Lint
flake8 app/
```

---

## 🚀 Deployment

### Production Checklist
- [ ] Update `ENVIRONMENT=production` in .env
- [ ] Set strong `SECRET_KEY` and `ADMIN_TOKEN`
- [ ] Configure production database
- [ ] Update CORS `allow_origins` in `main.py`
- [ ] Set up email service for password resets
- [ ] Enable HTTPS/SSL
- [ ] Configure error monitoring (e.g., Sentry)
- [ ] Set up automated backups
- [ ] Configure logging and monitoring
- [ ] Run security audit

### Environment Variables for Production
```env
DATABASE_HOSTNAME=your-prod-db-host
DATABASE_PORT=5432
DATABASE_USERNAME=rentwheels_user
DATABASE_PASSWORD=strong_random_password
DATABASE_NAME=rentwheels_prod
SECRET_KEY=generate-with-openssl-rand-base64-32
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ADMIN_TOKEN=generate-strong-admin-token
ADMIN_ALLOWED_HOSTS=your-server-ip
ENVIRONMENT=production
DEBUG=false
```

---

## 📚 Documentation

- **API Documentation**: Available at `/docs` (Swagger UI)
- **Alternative Docs**: Available at `/redoc` (ReDoc)
- **Password Reset Guide**: See `PASSWORD_RESET_USAGE.md`
- **Health Check**: `GET /health` - Check API and database status

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License.

---

## 👨‍💻 Author

**Humayun**
- GitHub: [@Humayun-23](https://github.com/Humayun-23)

---

## 🙏 Acknowledgments

- FastAPI for the amazing web framework
- SQLAlchemy for powerful ORM
- Pydantic for data validation
- PostgreSQL for reliable database
- All contributors and users of this project

---

## 📞 Support

For issues, questions, or contributions, please open an issue on GitHub.
