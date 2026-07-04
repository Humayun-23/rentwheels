import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.database import Base, get_db
from app.db.models import User, Shop, Bike, RentalStaff, BikeInventory
from app.utils.utils import hash_password
from app.api.v1.oauth2 import create_access_token

# We use an in-memory SQLite database for testing, which is fast and completely isolated.
SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def db_engine():
    """Create tables once per test session."""
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create a fresh database session for each test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client(db_session):
    """
    Test client fixture. 
    Overrides the database dependency so endpoints use the test SQLite database.
    """
    def override_get_db():
        yield db_session
        
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as c:
        yield c

# ---- AUTH HELPERS ----

def get_auth_headers(user: User):
    token = create_access_token(data={"user_id": user.id, "role": "user"})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def auth_headers():
    def _auth_headers(user: User):
        return get_auth_headers(user)
    return _auth_headers

# ---- DB FIXTURES ----

def create_test_user(db_session, email, user_type):
    hashed = hash_password("strongpassword123")
    user = User(
        email=email,
        password=hashed,
        firstname="Test",
        lastname="User",
        phone_number="1234567890",
        user_type=user_type,
        is_email_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def verified_customer(db_session):
    return create_test_user(db_session, "customer@example.com", "customer")

@pytest.fixture
def verified_owner(db_session):
    return create_test_user(db_session, "owner@example.com", "shop_owner")

@pytest.fixture
def other_owner(db_session):
    return create_test_user(db_session, "other_owner@example.com", "shop_owner")

@pytest.fixture
def staff_user(db_session):
    return create_test_user(db_session, "staff@example.com", "customer") 

@pytest.fixture
def inactive_staff_user(db_session):
    return create_test_user(db_session, "inactive_staff@example.com", "customer")

@pytest.fixture
def owner_shop(db_session, verified_owner):
    shop = Shop(
        name="Owner Shop",
        owner_id=verified_owner.id,
        phone_number="1111111111",
        address="123 Main St",
        city="City",
        rentalos_subscription_status="active",
    )
    db_session.add(shop)
    db_session.commit()
    db_session.refresh(shop)
    return shop

@pytest.fixture
def other_shop(db_session, other_owner):
    shop = Shop(
        name="Other Shop",
        owner_id=other_owner.id,
        phone_number="2222222222",
        address="456 Other St",
        city="Other City",
        rentalos_subscription_status="active",
    )
    db_session.add(shop)
    db_session.commit()
    db_session.refresh(shop)
    return shop

@pytest.fixture
def rental_staff(db_session, owner_shop, staff_user):
    staff = RentalStaff(
        shop_id=owner_shop.id,
        user_id=staff_user.id,
        role="staff",
        is_active=True
    )
    db_session.add(staff)
    db_session.commit()
    db_session.refresh(staff)
    return staff

@pytest.fixture
def inactive_rental_staff(db_session, owner_shop, inactive_staff_user):
    staff = RentalStaff(
        shop_id=owner_shop.id,
        user_id=inactive_staff_user.id,
        role="staff",
        is_active=False
    )
    db_session.add(staff)
    db_session.commit()
    db_session.refresh(staff)
    return staff

@pytest.fixture
def owner_bike(db_session, owner_shop):
    bike = Bike(
        shop_id=owner_shop.id,
        name="Test Bike",
        model="Test Model",
        bike_type="scooty",
        price_per_hour=100,
        price_per_day=1000,
        is_available=True
    )
    db_session.add(bike)
    db_session.commit()
    db_session.refresh(bike)
    # Add inventory
    inv = BikeInventory(bike_id=bike.id, shop_id=owner_shop.id, total_quantity=1, available_quantity=1)
    db_session.add(inv)
    db_session.commit()
    return bike

from app.db.models import RentalCustomer, RentalBooking, Booking
from app.utils import tz
from datetime import timedelta

@pytest.fixture
def rental_customer(db_session, owner_shop, staff_user):
    customer = RentalCustomer(
        shop_id=owner_shop.id,
        phone_number="5555555555",
        firstname="Rental",
        lastname="Customer",
        created_by_user_id=staff_user.id
    )
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)
    return customer

@pytest.fixture
def rental_booking(db_session, owner_shop, rental_customer, owner_bike, staff_user):
    now = tz.now()
    booking = RentalBooking(
        shop_id=owner_shop.id,
        customer_id=rental_customer.id,
        bike_id=owner_bike.id,
        staff_id=staff_user.id,
        start_time=now + timedelta(hours=1),
        end_time=now + timedelta(hours=2),
        status="draft"
    )
    db_session.add(booking)
    db_session.commit()
    db_session.refresh(booking)
    return booking

@pytest.fixture
def online_booking(db_session, owner_shop, verified_customer, owner_bike):
    now = tz.now()
    booking = Booking(
        customer_id=verified_customer.id,
        bike_id=owner_bike.id,
        start_time=now + timedelta(hours=1),
        end_time=now + timedelta(hours=2),
        status="pending",
        total_price=100
    )
    db_session.add(booking)
    db_session.commit()
    db_session.refresh(booking)
    return booking
