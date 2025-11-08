from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime

from app.api.v1.oauth2 import get_current_user
from app.db.database import get_db
from app.db.models import BikeInventory, Bike, Booking, Shop, User
from app.schemas.inventory import BikeInventoryCreate, BikeInventoryUpdate, BikeInventoryOut, InventoryAvailability

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.post("/", response_model=BikeInventoryOut, status_code=status.HTTP_201_CREATED)
def create_inventory(inventory: BikeInventoryCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create inventory record for a bike"""
   # Only shop owners can create inventory
    if current_user.user_type != "shop_owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shop owners can create inventory records"
        )

    # Check if bike exists
    bike = db.query(Bike).filter(Bike.id == inventory.bike_id).first()
    if not bike:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bike with ID {inventory.bike_id} not found"
        )

    # Check if the current user owns the shop that owns this bike
    shop = db.query(Shop).filter(Shop.id == bike.shop_id).first()
    if not shop or shop.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to create inventory for this bike"
        )

    # Check if inventory already exists for this bike
    existing = db.query(BikeInventory).filter(BikeInventory.bike_id == inventory.bike_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Inventory already exists for bike {inventory.bike_id}"
        )

    db_inventory = BikeInventory(
        bike_id=inventory.bike_id,
        total_quantity=inventory.total_quantity,
        available_quantity=inventory.total_quantity,
        rented_quantity=0
    )

    db.add(db_inventory)
    db.commit()
    db.refresh(db_inventory)
    return db_inventory


@router.get("/bike/{bike_id}", response_model=BikeInventoryOut)
def get_inventory_by_bike(bike_id: int, db: Session = Depends(get_db)):
    """Get inventory status for a specific bike"""
    inventory = db.query(BikeInventory).filter(BikeInventory.bike_id == bike_id).first()

    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No inventory found for bike {bike_id}"
        )

    return inventory


@router.get("/shop/{shop_id}", response_model=list[BikeInventoryOut])
def get_shop_inventory(
    shop_id: int,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    """Get all bike inventory in a shop with pagination"""
    # Check if shop exists
    shop = db.query(Shop).filter(Shop.id == shop_id).first()
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shop with ID {shop_id} not found"
        )

    # Get all bikes in this shop with their inventory
    inventories = db.query(BikeInventory).join(Bike).filter(
        Bike.shop_id == shop_id
    ).offset(skip).limit(limit).all()

    return inventories


@router.get("/available/{bike_id}", response_model=InventoryAvailability)
def check_availability(bike_id: int, db: Session = Depends(get_db)):
    """Check if a bike is available for booking"""
    inventory = db.query(BikeInventory).filter(BikeInventory.bike_id == bike_id).first()

    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No inventory found for bike {bike_id}"
        )

    return InventoryAvailability(
        bike_id=bike_id,
        is_available=inventory.available_quantity > 0,
        available_count=inventory.available_quantity,
        total_count=inventory.total_quantity
    )


@router.put("/{bike_id}", response_model=BikeInventoryOut)
def update_inventory(bike_id: int, inventory_update: BikeInventoryUpdate,current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update total quantity for a bike"""
    # Only shop owners can update inventory
    if current_user.user_type != "shop_owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shop owners can update inventory records"
        )
    
    inventory = db.query(BikeInventory).filter(BikeInventory.bike_id == bike_id).first()

    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No inventory found for bike {bike_id}"
        )

    # Verify ownership: check if the current user owns the shop that owns this bike
    bike = db.query(Bike).filter(Bike.id == bike_id).first()
    if bike:
        shop = db.query(Shop).filter(Shop.id == bike.shop_id).first()
        if not shop or shop.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to update inventory for this bike"
            )

    # Update total quantity
    old_total = inventory.total_quantity
    inventory.total_quantity = inventory_update.total_quantity

    # Adjust available quantity if total changed
    difference = inventory_update.total_quantity - old_total
    inventory.available_quantity += difference

    db.commit()
    db.refresh(inventory)
    return inventory


@router.get("/availability/timerange", response_model=list[InventoryAvailability])
def check_availability_range(shop_id: int, start_time: datetime, end_time: datetime, db: Session = Depends(get_db)):
    """Check availability of all bikes in a shop for a specific time range"""
    # Get all bikes in shop
    bikes = db.query(Bike).filter(Bike.shop_id == shop_id).all()

    availability_list = []

    for bike in bikes:
        # Count active bookings during the time range
        conflicting_bookings = db.query(Booking).filter(
            and_(
                Booking.bike_id == bike.id,
                Booking.status.in_(["confirmed", "pending"]),
                # Booking overlaps with requested time
                or_(
                    and_(Booking.start_time <= start_time, Booking.end_time > start_time),
                    and_(Booking.start_time < end_time, Booking.end_time >= end_time),
                    and_(Booking.start_time >= start_time, Booking.end_time <= end_time)
                )
            )
        ).count()

        inventory = db.query(BikeInventory).filter(BikeInventory.bike_id == bike.id).first()
        if inventory:
            available = inventory.available_quantity - conflicting_bookings

            availability_list.append(InventoryAvailability(
                bike_id=bike.id,
                is_available=available > 0,
                available_count=max(0, available),
                total_count=inventory.total_quantity
            ))

    return availability_list
