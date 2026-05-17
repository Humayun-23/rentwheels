from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Bike, Shop, User, BikeImage
from app.schemas.bikes import BikeCreate, BikeUpdate, BikeOut
from app.api.v1.oauth2 import get_current_user
from app.utils.cloudinary_client import upload_image

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

    db_bike = Bike(**bike.model_dump(exclude_unset=True))  # ✅ FIXED: Pydantic v2
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
def get_shop_bikes(
    shop_id: int, 
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    """Get all bikes in a shop with pagination"""
    shop = db.query(Shop).filter(Shop.id == shop_id).first()
    
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shop with ID {shop_id} not found"
        )
    
    bikes = db.query(Bike).filter(
        Bike.shop_id == shop_id
    ).offset(skip).limit(limit).all()
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
    
    for key, value in bike_update.model_dump(exclude_unset=True).items():  # ✅ FIXED: Pydantic v2
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


@router.post("/{bike_id}/images", response_model=BikeOut)
def upload_bike_images(
    bike_id: int,
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload up to 3 images for a bike"""
    bike = db.query(Bike).filter(Bike.id == bike_id).first()
    if not bike:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bike with ID {bike_id} not found",
        )

    shop = db.query(Shop).filter(Shop.id == bike.shop_id).first()
    if shop.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update bikes in your shop",
        )

    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one image is required",
        )
    if len(files) > 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can upload up to 3 images",
        )

    existing_count = db.query(BikeImage).filter(BikeImage.bike_id == bike_id).count()
    if existing_count + len(files) > 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can upload up to 3 images in total",
        )

    for file in files:
        image_url = upload_image(file, folder=f"bikes/{bike_id}")
        db.add(BikeImage(bike_id=bike_id, image_url=image_url))

    db.commit()
    db.refresh(bike)
    return bike
