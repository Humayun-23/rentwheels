from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from app.db.database import get_db
from app.db.models import Booking, Bike, BikeInventory, User
from app.schemas.booking import BookingCreate, BookingUpdate, BookingOut
from app.api.v1.oauth2 import get_current_user

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("/", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
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

    # Create booking
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
