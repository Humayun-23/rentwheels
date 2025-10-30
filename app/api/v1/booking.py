from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from datetime import datetime
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.main import app
from app.db.database import get_db
from app.db.models import Booking, Bike, BikeInventory, User, Shop
from app.schemas.booking import BookingCreate, BookingUpdate, BookingOut
from app.api.v1.oauth2 import get_current_user

router = APIRouter(prefix="/bookings", tags=["bookings"])


limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@router.post("/", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def homepage(request: Request):
    return PlainTextResponse("test")
def create_booking(booking: BookingCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new booking (customers only)"""
    if current_user.user_type != "customer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only customers can create bookings"
        )

    # Check if bike exists
    bike = db.query(Bike).filter(Bike.id == booking.bike_id).first()
    if not bike:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bike with ID {booking.bike_id} not found"
        )

    # Check if bike is available
    inventory = db.query(BikeInventory).filter(BikeInventory.bike_id == booking.bike_id).first()
    if not inventory or inventory.available_quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bike is not available for booking"
        )
    #checking if the same bike is already booked for the requested time range
    overlapping_booking = db.query(Booking).filter(
        Booking.bike_id == booking.bike_id,
        Booking.status.in_(["pending", "confirmed"]),
        Booking.start_time < booking.end_time,
        Booking.end_time > booking.start_time
    ).first()

    if overlapping_booking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid booking time range"
        )
    if booking.start_time < datetime.now():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking start time must be in the future"
        )
    db_booking = Booking(
        customer_id=current_user.id,
        bike_id=booking.bike_id,
        start_time=booking.start_time,
        end_time=booking.end_time,
        status="pending"
    )

    # Update inventory
    inventory.available_quantity -= 1
    inventory.rented_quantity += 1

    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    return db_booking


@router.get("/{booking_id}", response_model=BookingOut)
def get_booking(booking_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get a booking by ID"""
    if current_user.user_type != "customer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only customers can view bookings"
        )
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking with ID {booking_id} not found"
        )
    
    return booking


@router.get("/", response_model=list[BookingOut])
def get_user_bookings(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all bookings for current user"""
    bookings = db.query(Booking).filter(Booking.customer_id == current_user.id).all()
    return bookings


@router.put("/{booking_id}", response_model=BookingOut)
def update_booking(booking_id: int, booking_update: BookingUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update booking status"""
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking with ID {booking_id} not found"
        )
    
    if booking.customer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own bookings"
        )
    
    for key, value in booking_update.dict(exclude_unset=True).items():
        setattr(booking, key, value)
    
    db.commit()
    db.refresh(booking)
    return booking


@router.delete("/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_booking(booking_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Cancel a booking"""
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking with ID {booking_id} not found"
        )
    
    if booking.customer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only cancel your own bookings"
        )
    
    # Return inventory when booking is cancelled
    inventory = db.query(BikeInventory).filter(BikeInventory.bike_id == booking.bike_id).first()
    if inventory:
        inventory.available_quantity += 1
        inventory.rented_quantity -= 1
    
    db.delete(booking)
    db.commit()


@router.post("/{booking_id}/confirm", response_model=BookingOut)
def confirm_booking(booking_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Confirm a pending booking (shop owners only)"""
    if current_user.user_type != "shop_owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shop owners can confirm bookings"
        )
    
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking with ID {booking_id} not found"
        )
    
    # Verify that the current user owns the shop that owns the bike
    bike = db.query(Bike).filter(Bike.id == booking.bike_id).first()
    if not bike:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bike not found"
        )
    
    shop = db.query(Shop).filter(Shop.id == bike.shop_id).first()
    if not shop or shop.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only confirm bookings for bikes in your shop"
        )
    
    # Only pending bookings can be confirmed
    if booking.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot confirm booking with status '{booking.status}'. Only pending bookings can be confirmed."
        )
    
    
    booking.status = "confirmed"
    booking.confirmed_at = datetime.utcnow()
    db.commit()
    db.refresh(booking)
    return booking


@router.post("/{booking_id}/reject", response_model=BookingOut)
def reject_booking(booking_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Reject a pending booking (shop owners only)"""
    if current_user.user_type != "shop_owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shop owners can reject bookings"
        )
    
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking with ID {booking_id} not found"
        )
    
    # Verify that the current user owns the shop that owns the bike
    bike = db.query(Bike).filter(Bike.id == booking.bike_id).first()
    if not bike:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bike not found"
        )
    
    shop = db.query(Shop).filter(Shop.id == bike.shop_id).first()
    if not shop or shop.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only reject bookings for bikes in your shop"
        )
    
    # Only pending bookings can be rejected
    if booking.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject booking with status '{booking.status}'. Only pending bookings can be rejected."
        )
    
    # Return inventory when booking is rejected
    inventory = db.query(BikeInventory).filter(BikeInventory.bike_id == booking.bike_id).first()
    if inventory:
        inventory.available_quantity += 1
        inventory.rented_quantity -= 1
    
    booking.status = "cancelled"
    db.commit()
    db.refresh(booking)
    return booking

@router.post("/{booking_id}/complete", response_model=BookingOut)
def complete_booking(booking_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Mark a booking as completed (shop owners only)"""
    if current_user.user_type != "shop_owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shop owners can complete bookings"
        )
    
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking with ID {booking_id} not found"
        )
    
    # Verify that the current user owns the shop that owns the bike
    bike = db.query(Bike).filter(Bike.id == booking.bike_id).first()
    if not bike:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bike not found"
        )
    
    shop = db.query(Shop).filter(Shop.id == bike.shop_id).first()
    if not shop or shop.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only complete bookings for bikes in your shop"
        )
    
    # Only confirmed bookings can be completed
    if booking.status != "confirmed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot complete booking with status '{booking.status}'. Only confirmed bookings can be completed."
        )
    # Return inventory when booking is completed
    inventory = db.query(BikeInventory).filter(BikeInventory.bike_id == booking.bike_id).first()
    if inventory:
        inventory.available_quantity += 1
        inventory.rented_quantity -= 1
    booking.status = "completed"
    booking.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(booking)
    return booking
