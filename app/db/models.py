from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Time, UniqueConstraint, Float
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
    rental_staff_memberships = relationship("RentalStaff", back_populates="user", foreign_keys="RentalStaff.user_id")


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
    rentalos_subscription_status = Column(String, default="inactive")
    rentalos_subscription_end_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=tz.now)
    updated_at = Column(DateTime, default=tz.now, onupdate=tz.now)

    # Relationship: Many shops belong to one user
    owner = relationship("User", back_populates="shops", foreign_keys=[owner_id])
    bikes = relationship("Bike", back_populates="shop", cascade="all, delete-orphan")
    image = relationship("ShopImage", back_populates="shop", cascade="all, delete-orphan")
    rental_staff = relationship("RentalStaff", back_populates="shop", cascade="all, delete-orphan")
    rental_customers = relationship("RentalCustomer", back_populates="shop", cascade="all, delete-orphan")
    rental_bookings = relationship("RentalBooking", back_populates="shop", cascade="all, delete-orphan")


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
    maintenance_status = Column(String, default="available") # "available", "maintenance", "repair", "cleaning"
    created_at = Column(DateTime, default=tz.now)
    updated_at = Column(DateTime, default=tz.now, onupdate=tz.now)

    # Relationship: Many bikes belong to one shop
    shop = relationship("Shop", back_populates="bikes", foreign_keys=[shop_id])
    bookings = relationship("Booking", back_populates="bike", cascade="all, delete-orphan")
    inventory = relationship("BikeInventory", back_populates="bike", uselist=False, cascade="all, delete-orphan")
    image = relationship("BikeImage", back_populates="bike", cascade="all, delete-orphan")
    rental_bookings = relationship("RentalBooking", back_populates="bike", cascade="all, delete-orphan")


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


class RentalStaff(Base):
    """RentalOS staff membership for a shop."""
    __tablename__ = "rental_staff"

    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(Integer, ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String, nullable=False, default="staff")  # "staff" or "owner"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=tz.now)
    updated_at = Column(DateTime, default=tz.now, onupdate=tz.now)

    __table_args__ = (
        UniqueConstraint("shop_id", "user_id", name="uq_rental_staff_shop_user"),
    )

    shop = relationship("Shop", back_populates="rental_staff", foreign_keys=[shop_id])
    user = relationship("User", back_populates="rental_staff_memberships", foreign_keys=[user_id])
    bookings = relationship("RentalBooking", back_populates="staff", foreign_keys="RentalBooking.staff_id")


class RentalCustomer(Base):
    """RentalOS offline customer record scoped to one shop."""
    __tablename__ = "rental_customers"

    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(Integer, ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True)
    phone_number = Column(String, nullable=False, index=True)
    email = Column(String, nullable=True)
    firstname = Column(String, nullable=True)
    lastname = Column(String, nullable=True)
    document_consent = Column(Boolean, default=False)
    document_consent_at = Column(DateTime, nullable=True)
    marketing_consent = Column(Boolean, default=False)
    marketing_consent_at = Column(DateTime, nullable=True)
    current_flag_status = Column(String, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime, default=tz.now)
    updated_at = Column(DateTime, default=tz.now, onupdate=tz.now)

    __table_args__ = (
        UniqueConstraint("shop_id", "phone_number", name="uq_rental_customers_shop_phone"),
    )

    shop = relationship("Shop", back_populates="rental_customers", foreign_keys=[shop_id])
    created_by_user = relationship("User", foreign_keys=[created_by_user_id])
    bookings = relationship("RentalBooking", back_populates="customer", cascade="all, delete-orphan")
    flags = relationship("RentalCustomerFlag", back_populates="customer", cascade="all, delete-orphan")


class RentalCustomerFlag(Base):
    """RentalOS customer flag visible during counter lookup."""
    __tablename__ = "rental_customer_flags"

    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(Integer, ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("rental_customers.id", ondelete="CASCADE"), nullable=False, index=True)
    flag_type = Column(String, nullable=False)
    severity = Column(String, nullable=False, default="info")  # "info", "warning", "blocked"
    note = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime, default=tz.now)
    updated_at = Column(DateTime, default=tz.now, onupdate=tz.now)

    shop = relationship("Shop", foreign_keys=[shop_id])
    customer = relationship("RentalCustomer", back_populates="flags", foreign_keys=[customer_id])
    created_by_user = relationship("User", foreign_keys=[created_by_user_id])


class RentalBooking(Base):
    """RentalOS offline counter booking separate from online marketplace bookings."""
    __tablename__ = "rental_bookings"

    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(Integer, ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("rental_customers.id", ondelete="CASCADE"), nullable=False, index=True)
    bike_id = Column(Integer, ForeignKey("bikes.id", ondelete="CASCADE"), nullable=False, index=True)
    staff_id = Column(Integer, ForeignKey("rental_staff.id", ondelete="SET NULL"), nullable=True, index=True)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False, index=True)
    status = Column(String, nullable=False, default="draft", index=True)  # "draft", "confirmed", "active", "completed", "cancelled"
    total_amount = Column(Integer, nullable=True)
    advance_paid = Column(Integer, nullable=False, default=0)
    balance_due = Column(Integer, nullable=False, default=0)
    security_deposit = Column(Integer, nullable=False, default=0)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=tz.now)
    updated_at = Column(DateTime, default=tz.now, onupdate=tz.now)

    shop = relationship("Shop", back_populates="rental_bookings", foreign_keys=[shop_id])
    customer = relationship("RentalCustomer", back_populates="bookings", foreign_keys=[customer_id])
    bike = relationship("Bike", back_populates="rental_bookings", foreign_keys=[bike_id])
    staff = relationship("RentalStaff", back_populates="bookings", foreign_keys=[staff_id])
    documents = relationship("RentalBookingDocument", back_populates="booking", cascade="all, delete-orphan")
    handover_photos = relationship("RentalHandoverPhoto", back_populates="booking", cascade="all, delete-orphan")
    payments = relationship("RentalPayment", back_populates="booking", cascade="all, delete-orphan")
    notes = relationship("RentalBookingNote", back_populates="booking", cascade="all, delete-orphan")


class RentalBookingDocument(Base):
    """RentalOS DL/ID proof uploaded for a counter booking."""
    __tablename__ = "rental_booking_documents"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("rental_bookings.id", ondelete="CASCADE"), nullable=False, index=True)
    document_type = Column(String, nullable=False)  # "driving_license" or "id_proof"
    file_url = Column(String, nullable=False)
    file_name = Column(String, nullable=True)
    content_type = Column(String, nullable=True)
    uploaded_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime, default=tz.now)

    booking = relationship("RentalBooking", back_populates="documents", foreign_keys=[booking_id])
    uploaded_by_user = relationship("User", foreign_keys=[uploaded_by_user_id])


class RentalHandoverPhoto(Base):
    """RentalOS customer-with-vehicle handover photo with optional location metadata."""
    __tablename__ = "rental_handover_photos"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("rental_bookings.id", ondelete="CASCADE"), nullable=False, index=True)
    image_url = Column(String, nullable=False)
    location_permission_granted = Column(Boolean, default=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    location_accuracy_meters = Column(Integer, nullable=True)
    location_address = Column(String, nullable=True)
    captured_at = Column(DateTime, nullable=True)
    uploaded_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime, default=tz.now)

    booking = relationship("RentalBooking", back_populates="handover_photos", foreign_keys=[booking_id])
    uploaded_by_user = relationship("User", foreign_keys=[uploaded_by_user_id])


class RentalPayment(Base):
    """RentalOS offline payment tracking for advance, balance, and security deposit."""
    __tablename__ = "rental_payments"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("rental_bookings.id", ondelete="CASCADE"), nullable=False, index=True)
    payment_type = Column(String, nullable=False)  # "advance", "balance", "security_deposit"
    amount = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="pending", index=True)  # "pending", "partial", "paid", "refunded"
    method = Column(String, nullable=True)
    reference_number = Column(String, nullable=True)
    paid_at = Column(DateTime, nullable=True)
    received_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime, default=tz.now)
    updated_at = Column(DateTime, default=tz.now, onupdate=tz.now)

    booking = relationship("RentalBooking", back_populates="payments", foreign_keys=[booking_id])
    received_by_user = relationship("User", foreign_keys=[received_by_user_id])


class RentalBookingNote(Base):
    """RentalOS optional booking/customer note."""
    __tablename__ = "rental_booking_notes"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("rental_bookings.id", ondelete="CASCADE"), nullable=False, index=True)
    note = Column(String, nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime, default=tz.now)

    booking = relationship("RentalBooking", back_populates="notes", foreign_keys=[booking_id])
    created_by_user = relationship("User", foreign_keys=[created_by_user_id])
