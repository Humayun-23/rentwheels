from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Time
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class User(Base):
    """User model - represents both customers and shop owners"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)  # Changed to String to support all phone formats
    user_type = Column(String, nullable=False)  # "customer" or "shop_owner"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship: One user can own multiple shops
    shops = relationship("Shop", back_populates="owner", foreign_keys="Shop.owner_id")
    # Relationship: One user (customer) can have multiple bookings
    bookings = relationship("Booking", back_populates="customer", foreign_keys="Booking.customer_id")


class Shop(Base):
    """Shop model - represents rental shops owned by users"""
    __tablename__ = "shops"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    phone_number = Column(String, nullable=False)  # Changed to String to support all phone formats
    address = Column(String, nullable=False)
    city = Column(String, nullable=False)
    state = Column(String, nullable=True)
    zip_code = Column(String, nullable=True)
    opening_time = Column(Time, nullable=True)
    closing_time = Column(Time, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship: Many shops belong to one user
    owner = relationship("User", back_populates="shops", foreign_keys=[owner_id])
    bikes = relationship("Bike", back_populates="shop", cascade="all, delete-orphan")


class Bike(Base):
    """Bike model - represents bikes available for rent in shops"""
    __tablename__ = "bikes"

    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(Integer, ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    model = Column(String, nullable=False)
    bike_type = Column(String, nullable=False)  # "scooty", "bike", "car", etc.
    engine_cc = Column(Integer, nullable=True)  # Engine displacement in CC (e.g., 150, 250, 500)
    description = Column(String, nullable=True)
    price_per_hour = Column(Integer, nullable=False)  # Price in cents
    price_per_day = Column(Integer, nullable=False)  # Price in cents
    condition = Column(String, nullable=False, default="good")  # "excellent", "good", "fair"
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship: Many bikes belong to one shop
    shop = relationship("Shop", back_populates="bikes", foreign_keys=[shop_id])
    bookings = relationship("Booking", back_populates="bike", cascade="all, delete-orphan")
    inventory = relationship("BikeInventory", back_populates="bike", uselist=False, cascade="all, delete-orphan")


class BikeInventory(Base):
    """BikeInventory model - tracks real-time inventory for each bike"""
    __tablename__ = "bike_inventory"

    id = Column(Integer, primary_key=True, index=True)
    bike_id = Column(Integer, ForeignKey("bikes.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    total_quantity = Column(Integer, nullable=False, default=1)  # Total bikes of this type
    available_quantity = Column(Integer, nullable=False, default=1)  # Available for booking
    rented_quantity = Column(Integer, nullable=False, default=0)  # Currently rented
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship: Each inventory record belongs to one bike
    bike = relationship("Bike", back_populates="inventory", foreign_keys=[bike_id])


class Booking(Base):
    """Booking model - represents bike rental bookings by customers"""
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    bike_id = Column(Integer, ForeignKey("bikes.id", ondelete="CASCADE"), nullable=False, index=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    status = Column(String, nullable=False, default="pending")  # "pending", "confirmed", "completed", "cancelled"
    total_price = Column(Integer, nullable=True)  # Price in cents
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    customer = relationship("User", back_populates="bookings", foreign_keys=[customer_id])
    bike = relationship("Bike", back_populates="bookings", foreign_keys=[bike_id])
