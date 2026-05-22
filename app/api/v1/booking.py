import secrets
from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.utils import tz

from app.utils.limiter import limiter
from app.db.database import get_db
from app.db.models import Booking, Bike, BikeInventory, User, Shop, Payment
from app.schemas.booking import BookingCreate, BookingUpdate, BookingOut
from app.api.v1.oauth2 import get_current_user

router = APIRouter(prefix="/bookings", tags=["bookings"])


def calculate_booking_price(bike: Bike, start_time, end_time) -> int:
    duration = end_time - start_time
    total_hours = max(duration.total_seconds() / 3600, 1)
    full_days = int(total_hours // 24)
    remaining_hours = total_hours - (full_days * 24)
    return int((full_days * bike.price_per_day) + (remaining_hours * bike.price_per_hour))


def verify_shop_ownership(booking: Booking, current_user: User, db: Session, action: str = "manage") -> None:
    """Helper function to verify that the current user owns the shop that owns the bike in the booking"""
    if current_user.user_type != "shop_owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Only shop owners can {action} bookings"
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
            detail=f"You can only {action} bookings for bikes in your shop"
        )


@router.post("/", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def create_booking(request: Request, booking: BookingCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new booking (customers only)"""
    if current_user.user_type != "customer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only customers can create bookings"
        )

    start_time = tz.ensure_aware(booking.start_time)
    end_time = tz.ensure_aware(booking.end_time)

    # Check if bike exists
    bike = db.query(Bike).filter(Bike.id == booking.bike_id).first()
    if not bike:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bike with ID {booking.bike_id} not found"
        )

    if end_time <= start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking end time must be after the start time"
        )

    # ✅ FIXED: Booking duration validation
    from datetime import timedelta
    MIN_BOOKING_HOURS = 1
    MAX_BOOKING_DAYS = 30
    
    duration = end_time - start_time
    if duration < timedelta(hours=MIN_BOOKING_HOURS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Booking must be at least {MIN_BOOKING_HOURS} hour(s)"
        )
    
    if duration > timedelta(days=MAX_BOOKING_DAYS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Booking cannot exceed {MAX_BOOKING_DAYS} days"
        )

    # Check if bike is available with row-level lock to prevent race conditions
    inventory = db.query(BikeInventory).filter(
        BikeInventory.bike_id == booking.bike_id
    ).with_for_update().first()
    
    if not inventory or inventory.available_quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bike is not available for booking"
        )
    # checking if the bike has enough capacity for the requested time range
    conflicting_bookings = db.query(Booking).filter(
        Booking.bike_id == booking.bike_id,
        Booking.status.in_(["pending", "confirmed", "paid"]),
        Booking.start_time < end_time,
        Booking.end_time > start_time
    ).count()

    if conflicting_bookings >= inventory.available_quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bike is fully booked for the requested time range"
        )
    if start_time < tz.now():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking start time must be in the future"
        )
    db_booking = Booking(
        customer_id=current_user.id,
        bike_id=booking.bike_id,
        start_time=start_time,
        end_time=end_time,
        status="pending",
        total_price=calculate_booking_price(bike, start_time, end_time),
        magic_token=secrets.token_urlsafe(16),
    )

    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    return db_booking


@router.get("/user/", response_model=list[BookingOut])
def get_user_bookings(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Get all bookings for current user with pagination"""
    bookings = db.query(Booking).filter(
        Booking.customer_id == current_user.id
    ).offset(skip).limit(limit).all()
    return bookings


@router.get("/", response_model=list[BookingOut])
def list_bookings(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List bookings visible to the current user.

    Customers see their own bookings. Shop owners see bookings for vehicles in
    shops they own, which lets them confirm/reject pending requests.
    """
    if current_user.user_type == "customer":
        return db.query(Booking).filter(
            Booking.customer_id == current_user.id
        ).offset(skip).limit(limit).all()

    if current_user.user_type == "shop_owner":
        return (
            db.query(Booking)
            .join(Bike, Booking.bike_id == Bike.id)
            .join(Shop, Bike.shop_id == Shop.id)
            .filter(Shop.owner_id == current_user.id)
            .offset(skip)
            .limit(limit)
            .all()
        )
        
    if current_user.user_type == "admin":
        return db.query(Booking).offset(skip).limit(limit).all()

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to list bookings",
    )


@router.get("/{booking_id}", response_model=BookingOut)
def get_booking(booking_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get a booking by ID for the customer or owning shop."""
    booking = db.query(Booking).filter(Booking.id == booking_id).first()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking with ID {booking_id} not found"
        )

    if current_user.user_type == "customer":
        if booking.customer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own bookings"
            )
        return booking

    verify_shop_ownership(booking, current_user, db, "view")
    return booking

@router.put("/{booking_id}", response_model=BookingOut)
def update_booking(booking_id: int, booking_update: BookingUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update a pending booking's time range."""
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

    if booking.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending bookings can be updated"
        )

    if booking_update.status is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking status must be changed through booking actions"
        )

    new_start_time = tz.ensure_aware(booking_update.start_time or booking.start_time)
    new_end_time = tz.ensure_aware(booking_update.end_time or booking.end_time)
    if new_start_time < tz.now():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking start time must be in the future"
        )
    if new_end_time <= new_start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking end time must be after the start time"
        )

    inventory = db.query(BikeInventory).filter(BikeInventory.bike_id == booking.bike_id).with_for_update().first()
    conflicting_bookings = db.query(Booking).filter(
        Booking.bike_id == booking.bike_id,
        Booking.id != booking.id,
        Booking.status.in_(["pending", "confirmed", "paid"]),
        Booking.start_time < new_end_time,
        Booking.end_time > new_start_time
    ).count()
    
    if not inventory or conflicting_bookings >= inventory.available_quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bike is fully booked for the requested time range"
        )

    bike = db.query(Bike).filter(Bike.id == booking.bike_id).first()
    booking.start_time = new_start_time
    booking.end_time = new_end_time
    if bike:
        booking.total_price = calculate_booking_price(bike, new_start_time, new_end_time)
    
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
    
    if booking.status in {"cancelled", "completed", "refunded"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel a booking with status '{booking.status}'"
        )
    if booking.status in {"paid", "refund_pending"}:
        paid_payment = db.query(Payment).filter(Payment.booking_id == booking.id, Payment.status == "paid").first()
        if paid_payment:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Paid bookings must be cancelled through the refund flow"
            )

    booking.status = "cancelled"
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
    
        # Verify that the current user owns the shop
    verify_shop_ownership(booking, current_user, db, "confirm")
    
    # Only pending bookings can be confirmed
    if booking.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot confirm booking with status '{booking.status}'. Only pending bookings can be confirmed."
        )
    
    
    booking.status = "confirmed"
    booking.confirmed_at = tz.now()
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
    
        # Verify that the current user owns the shop
    verify_shop_ownership(booking, current_user, db, "reject")
    
    # Only pending bookings can be rejected
    if booking.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject booking with status '{booking.status}'. Only pending bookings can be rejected."
        )
    
    booking.status = "cancelled"
    db.commit()
    db.refresh(booking)
    return booking

@router.post("/{booking_id}/complete", response_model=BookingOut)
def complete_booking(booking_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Mark a booking as completed (shop owners only)"""
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking with ID {booking_id} not found"
        )
    
    # Verify that the current user owns the shop
    verify_shop_ownership(booking, current_user, db, "complete")
    
    # Only confirmed bookings can be completed
    if booking.status not in {"confirmed", "paid"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot complete booking with status '{booking.status}'. Only confirmed or paid bookings can be completed."
        )
        
    booking.status = "completed"
    booking.completed_at = tz.now()
    db.commit()
    db.refresh(booking)
    return booking


@router.post("/{booking_id}/return", response_model=BookingOut)
def return_booking(booking_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Mark a booking as returned/completed and update inventory (shop owners only)"""
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking with ID {booking_id} not found"
        )
    
    # Verify that the current user owns the shop
    verify_shop_ownership(booking, current_user, db, "return")
    
    # Only confirmed or paid bookings can be marked as returned
    if booking.status not in {"confirmed", "paid", "completed"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot mark booking as returned with status '{booking.status}'. Only confirmed, paid, or completed bookings can be returned."
        )
    
    booking.status = "returned"
    db.commit()
    db.refresh(booking)
    return booking

@router.get("/{booking_id}/magic-action", response_class=HTMLResponse)
def magic_action(booking_id: int, action: str, token: str, db: Session = Depends(get_db)):
    """Handle Magic Links for WhatsApp quick actions (no auth required)."""
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    
    def render_html(emoji, title, message, color="#374151"):
        return f"""
        <html>
            <body style="font-family: system-ui, sans-serif; text-align: center; background-color: #f3f4f6; padding: 2rem;">
                <div style="max-width: 400px; margin: 0 auto; background: white; padding: 2rem; border-radius: 1rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <div style="font-size: 4rem; margin-bottom: 1rem;">{emoji}</div>
                    <h1 style="color: {color}; margin-top: 0;">{title}</h1>
                    <p style="color: #6b7280; font-size: 1.1rem;">{message}</p>
                </div>
            </body>
        </html>
        """
        
    if not booking:
        return render_html("❌", "Not Found", "We couldn't find this booking in the system.")
    if not getattr(booking, "magic_token", None) or booking.magic_token != token:
        return render_html("🔒", "Invalid Link", "This magic link is invalid or has expired.")
    if booking.status != "pending":
        return render_html("⚠️", "Already Processed", f"This booking was already marked as {booking.status.upper()}.")
        
    if action == "confirm":
        booking.status = "confirmed"
        booking.confirmed_at = tz.now()
        db.commit()
        return render_html("✅", "Booking Confirmed!", "The customer has been notified and can now pay.", "#10b981")
    elif action == "reject":
        booking.status = "cancelled"
        db.commit()
        return render_html("⛔", "Booking Rejected", "The booking has been cancelled successfully.", "#ef4444")
        
    return render_html("❓", "Unknown Action", "We didn't understand that action.")
