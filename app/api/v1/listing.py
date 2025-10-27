from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Bike, Shop, User
from app.schemas.bikes import BikeCreate, BikeUpdate, BikeOut
from app.api.v1.oauth2 import get_current_user

router = APIRouter(prefix="/bikes", tags=["bikes"])


@router.post("/", response_model=BikeOut, status_code=status.HTTP_201_CREATED)
def create_bike(bike: BikeCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new bike (shop owners only)"""
    if current_user.user_type != "shop_owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shop owners can add bikes"
        )

    # Check if shop exists and belongs to user
    shop = db.query(Shop).filter(Shop.id == bike.shop_id).first()
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shop with ID {bike.shop_id} not found"
        )
    
    if shop.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only add bikes to your own shop"
        )

    db_bike = Bike(**bike.dict())
    db.add(db_bike)
    db.commit()
    db.refresh(db_bike)
    return db_bike


@router.get("/{bike_id}", response_model=BikeOut)
def get_bike(bike_id: int, db: Session = Depends(get_db)):
    """Get a bike by ID"""
    bike = db.query(Bike).filter(Bike.id == bike_id).first()
    
    if not bike:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bike with ID {bike_id} not found"
        )
    
    return bike


@router.get("/shop/{shop_id}", response_model=list[BikeOut])
def get_shop_bikes(shop_id: int, db: Session = Depends(get_db)):
    """Get all bikes in a shop"""
    shop = db.query(Shop).filter(Shop.id == shop_id).first()
    
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shop with ID {shop_id} not found"
        )
    
    bikes = db.query(Bike).filter(Bike.shop_id == shop_id).all()
    return bikes


@router.put("/{bike_id}", response_model=BikeOut)
def update_bike(bike_id: int, bike_update: BikeUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update a bike (owner only)"""
    bike = db.query(Bike).filter(Bike.id == bike_id).first()
    
    if not bike:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bike with ID {bike_id} not found"
        )
    
    shop = db.query(Shop).filter(Shop.id == bike.shop_id).first()
    if shop.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update bikes in your shop"
        )
    
    for key, value in bike_update.dict(exclude_unset=True).items():
        setattr(bike, key, value)
    
    db.commit()
    db.refresh(bike)
    return bike


@router.delete("/{bike_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bike(bike_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a bike (owner only)"""
    bike = db.query(Bike).filter(Bike.id == bike_id).first()
    
    if not bike:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bike with ID {bike_id} not found"
        )
    
    shop = db.query(Shop).filter(Shop.id == bike.shop_id).first()
    if shop.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete bikes from your shop"
        )
    
    db.delete(bike)
    db.commit()
