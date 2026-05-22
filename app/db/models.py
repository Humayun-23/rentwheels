from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Time
from sqlalchemy.orm import relationship
from app.utils import tz
from .database import Base


class User(Base):
    """User model - represents both customers and shop owners"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    firstname = Column(String, nullable=False)
    lastname = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)  # Changed to String to support all phone formats
    user_type = Column(String, nullable=False)  # "customer" or "shop_owner"
    is_email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=tz.now)
    updated_at = Column(DateTime, default=tz.now, onupdate=tz.now)

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
    upi_id = Column(String(50), nullable=True)
    address = Column(String, nullable=False)
    city = Column(String, nullable=False)
    state = Column(String, nullable=True)
    zip_code = Column(String, nullable=True)
    opening_time = Column(Time, nullable=True)
    closing_time = Column(Time, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=tz.now)
    updated_at = Column(DateTime, default=tz.now, onupdate=tz.now)

    # Relationship: Many shops belong to one user
    owner = relationship("User", back_populates="shops", foreign_keys=[owner_id])
    bikes = relationship("Bike", back_populates="shop", cascade="all, delete-orphan")
    image = relationship("ShopImage", back_populates="shop", cascade="all, delete-orphan")


class ShopImage(Base):
    """ShopImage model - stores shop photos"""
    __tablename__ = "shop_images"

    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(Integer, ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True)
    image_url = Column(String, nullable=False)
    created_at = Column(DateTime, default=tz.now)

    shop = relationship("Shop", back_populates="image", foreign_keys=[shop_id])


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
    created_at = Column(DateTime, default=tz.now)
    updated_at = Column(DateTime, default=tz.now, onupdate=tz.now)

    # Relationship: Many bikes belong to one shop
    shop = relationship("Shop", back_populates="bikes", foreign_keys=[shop_id])
    bookings = relationship("Booking", back_populates="bike", cascade="all, delete-orphan")
    inventory = relationship("BikeInventory", back_populates="bike", uselist=False, cascade="all, delete-orphan")
    image = relationship("BikeImage", back_populates="bike", cascade="all, delete-orphan")


class BikeImage(Base):
    """BikeImage model - stores vehicle photos"""
    __tablename__ = "bike_images"

    id = Column(Integer, primary_key=True, index=True)
    bike_id = Column(Integer, ForeignKey("bikes.id", ondelete="CASCADE"), nullable=False, index=True)
    image_url = Column(String, nullable=False)
    created_at = Column(DateTime, default=tz.now)

    bike = relationship("Bike", back_populates="image", foreign_keys=[bike_id])


class BikeInventory(Base):
    """BikeInventory model - tracks real-time inventory for each bike"""
    __tablename__ = "bike_inventory"

    id = Column(Integer, primary_key=True, index=True)
    bike_id = Column(Integer, ForeignKey("bikes.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    shop_id = Column(Integer, ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True)
    total_quantity = Column(Integer, nullable=False, default=1)  # Total bikes of this type
    available_quantity = Column(Integer, nullable=False, default=1)  # Available for booking
    rented_quantity = Column(Integer, nullable=False, default=0)  # Currently rented
    created_at = Column(DateTime, default=tz.now)
    updated_at = Column(DateTime, default=tz.now, onupdate=tz.now)

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
    magic_token = Column(String(32), nullable=True)
    status = Column(String, nullable=False, default="pending")  # "pending", "confirmed", "completed", "cancelled"
    utr_number = Column(String(12), nullable=True)
    token_amount = Column(Integer, nullable=True) 
    total_price = Column(Integer, nullable=True)  # Price in inr
    created_at = Column(DateTime, default=tz.now)
    updated_at = Column(DateTime, default=tz.now, onupdate=tz.now)
    confirmed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    customer = relationship("User", back_populates="bookings", foreign_keys=[customer_id])
    bike = relationship("Bike", back_populates="bookings", foreign_keys=[bike_id])

class Review(Base):
    """Review model - represents customer reviews for shops"""
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    shop_id = Column(Integer, ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True)
    rating = Column(Integer, nullable=False)  # Rating out of 5
    comment = Column(String, nullable=True)
    created_at = Column(DateTime, default=tz.now)
    updated_at = Column(DateTime, default=tz.now, onupdate=tz.now)

    # Relationships
    shop = relationship("Shop", foreign_keys=[shop_id])
    customer = relationship("User", foreign_keys=[customer_id])
    
class AdminUser(Base):
    """AdminUser model - represents admin users of the system"""
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    created_at = Column(DateTime, default=tz.now)
    updated_at = Column(DateTime, default=tz.now, onupdate=tz.now)


class PasswordResetToken(Base):
    """PasswordResetToken model - stores password reset tokens"""
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=tz.now)

    # Relationship
    user = relationship("User", foreign_keys=[user_id])


class EmailVerificationToken(Base):
    """EmailVerificationToken model - stores email verification tokens"""
    __tablename__ = "email_verification_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=tz.now)

    user = relationship("User", foreign_keys=[user_id])
    
class Payment(Base):
    __tablename__ = "payment"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, unique=True, nullable=False, index=True)
    payment_id = Column(String, unique=True, nullable=True, index=True)
    refund_id = Column(String, unique=True, nullable=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Integer, nullable=False)  # Amount in paise for Razorpay
    refunded_amount = Column(Integer, nullable=False, default=0)
    currency = Column(String, nullable=False, default="INR")
    razorpay_signature = Column(String, nullable=True)
    status = Column(String, nullable=False, default="created")  # "created", "paid", "failed", "refunded", "refund_pending"
    created_at = Column(DateTime, default=tz.now)
    updated_at = Column(DateTime, default=tz.now, onupdate=tz.now)
    
