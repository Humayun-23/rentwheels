# About the Project
A backend APPI written in FastAPI. It is a platform where physical rent shop owners can list their vehicles and customers can book them.
# RentWheels API - Project Setup Complete ✅

## 📦 Project Structure


```
rentwheels/
├── app/
│   ├── main.py                 # FastAPI app & router setup
│   ├── config.py               # Settings (from .env)
│   ├── requirements.txt         # Python dependencies
│   ├── db/
│   │   ├── database.py         # SQLAlchemy setup
│   │   ├── models.py           # ORM models (User, Shop, Bike, Booking, BikeInventory)
│   ├── schemas/
│   │   ├── users.py            # User schemas
│   │   ├── shops.py            # Shop schemas
│   │   ├── bikes.py            # Bike schemas
│   │   ├── booking.py          # Booking schemas
│   │   ├── inventory.py        # Inventory schemas
│   │   ├── token.py            # Auth token schemas
│   ├── api/v1/
│   │   ├── auth.py             # Login endpoint
│   │   ├── oauth2.py           # JWT & auth utilities
│   │   ├── users.py            # User CRUD endpoints
│   │   ├── shops.py            # Shop CRUD endpoints
│   │   ├── listing.py          # Bike CRUD endpoints
│   │   ├── booking.py          # Booking endpoints
│   │   ├── inventory.py        # Inventory endpoints
│   ├── utils/
│   │   ├── utils.py            # Password hashing utilities
├── .env.example                # Environment variables template
└── README.md
```

---

## 🔧 Setup Instructions

### 1. Install Dependencies
```bash
pip install -r app/requirements.txt
```

### 2. Create .env file
```bash
cp .env.example .env
# Edit .env with your PostgreSQL credentials
```

### 3. Create PostgreSQL Database
```bash
createdb rentwheels
```

### 4. Run the Application
```bash
cd app
python main.py
```

API will be available at `http://localhost:8000`
- Docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 🔐 API Endpoints

### Authentication
- `POST /api/v1/login` - Login and get JWT token

### Users
- `POST /api/v1/users/` - Register new user
- `GET /api/v1/users/{user_id}` - Get user by ID
- `GET /api/v1/users/` - Get all users
- `PUT /api/v1/users/{user_id}` - Update user

### Shops
- `POST /api/v1/shops/` - Create shop (shop_owner only)
- `GET /api/v1/shops/{shop_id}` - Get shop details
- `GET /api/v1/shops/` - Get all shops
- `PUT /api/v1/shops/{shop_id}` - Update shop (owner only)
- `DELETE /api/v1/shops/{shop_id}` - Delete shop (owner only)

### Bikes (Listing)
- `POST /api/v1/bikes/` - Add bike to shop (shop_owner only)
- `GET /api/v1/bikes/{bike_id}` - Get bike details
- `GET /api/v1/bikes/shop/{shop_id}` - Get all bikes in shop
- `PUT /api/v1/bikes/{bike_id}` - Update bike (owner only)
- `DELETE /api/v1/bikes/{bike_id}` - Delete bike (owner only)

### Bookings
- `POST /api/v1/bookings/` - Create booking (customer only)
- `GET /api/v1/bookings/{booking_id}` - Get booking details
- `GET /api/v1/bookings/` - Get user's bookings
- `PUT /api/v1/bookings/{booking_id}` - Update booking status
- `DELETE /api/v1/bookings/{booking_id}` - Cancel booking

### Inventory
- `POST /api/v1/inventory/` - Create inventory record
- `GET /api/v1/inventory/bike/{bike_id}` - Get bike inventory
- `GET /api/v1/inventory/shop/{shop_id}` - Get shop inventory
- `GET /api/v1/inventory/available/{bike_id}` - Check availability
- `PUT /api/v1/inventory/{bike_id}` - Update quantity
- `GET /api/v1/inventory/availability/timerange` - Check time-range availability

---

## 📊 Database Models

### User
- `id`, `email`, `password`, `phone_number`, `user_type` (customer/shop_owner)
- Relationships: `shops[]`, `bookings[]`

### Shop
- `id`, `name`, `description`, `owner_id`, `phone_number`, `address`, `city`, `state`, `zip_code`
- `opening_time`, `closing_time`, `is_active`
- Relationships: `owner`, `bikes[]`

### Bike
- `id`, `shop_id`, `name`, `model`, `bike_type`, `description`
- `price_per_hour`, `price_per_day`, `condition`, `is_available`
- Relationships: `shop`, `bookings[]`, `inventory`

### BikeInventory
- `id`, `bike_id`, `total_quantity`, `available_quantity`, `rented_quantity`
- Real-time inventory tracking

### Booking
- `id`, `customer_id`, `bike_id`, `start_time`, `end_time`
- `status` (pending/confirmed/completed/cancelled), `total_price`
- Relationships: `customer`, `bike`

---

## 🔑 User Types & Permissions

### Customer
- ✅ Register account
- ✅ View shops and bikes
- ✅ Check availability
- ✅ Create bookings
- ✅ Cancel bookings
- ❌ Create shops
- ❌ Add bikes

### Shop Owner
- ✅ Register account
- ✅ Create shop
- ✅ Add bikes to shop
- ✅ Update bike inventory
- ✅ View bookings
- ❌ Create bookings (must use customer account)

---

## 🚀 Next Steps

1. **Migrations** - Set up Alembic for database versioning
2. **Testing** - Add pytest test suite
3. **Documentation** - Generate OpenAPI docs
4. **Deployment** - Deploy to cloud (AWS, Heroku, etc.)
5. **Features** - Add:
   - Payment processing
   - Email notifications
   - Rating system
   - Advanced search/filtering

---

## ⚙️ Environment Variables (.env)

```
DATABASE_HOSTNAME=localhost
DATABASE_PORT=5432
DATABASE_USERNAME=postgres
DATABASE_PASSWORD=your_password
DATABASE_NAME=rentwheels
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

---

## 📝 Sample API Calls

### Register
```bash
curl -X POST "http://localhost:8000/api/v1/users/" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "password123",
    "phone_number": 9876543210,
    "user_type": "customer"
  }'
```

### Login
```bash
curl -X POST "http://localhost:8000/api/v1/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=john@example.com&password=password123"
```

### Create Shop
```bash
curl -X POST "http://localhost:8000/api/v1/shops/" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Johns Bikes",
    "address": "123 Main St",
    "city": "New York"
  }'
```

---

All files created and configured! 🎉
