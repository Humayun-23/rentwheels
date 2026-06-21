from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Bike, Shop, User, BikeImage, BikeInventory, Review, ServiceLog
from app.schemas.bikes import BikeCreate, BikeUpdate, BikeOut, ServiceLogCreate, ServiceLogOut
from app.api.v1.oauth2 import get_current_user
from app.utils.cloudinary_client import upload_image

router = APIRouter(prefix="/bikes", tags=["bikes"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB

def optimize_cloudinary_url(url: str, width: int = 800) -> str:
    """Inject Cloudinary optimization flags (q_auto, f_auto) and resize."""
    if url and "cloudinary.com" in url and "/upload/" in url:
        parts = url.split("/upload/")
        return f"{parts[0]}/upload/q_auto,f_auto,w_{width}/{parts[1]}"
    return url

@router.post("/", response_model=BikeOut, status_code=status.HTTP_201_CREATED)
def create_bike(bike: BikeCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new bike (shop owners only)"""
    if current_user.user_type not in ["shop_owner"]:
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
    db.flush()
    db.add(BikeInventory(
        bike_id=db_bike.id,
        shop_id=shop.id,
        total_quantity=1,
        available_quantity=1,
        rented_quantity=0,
    ))
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


@router.get("/{bike_id}/full-details")
def get_bike_full_details(bike_id: int, db: Session = Depends(get_db)):
    """Get all vehicle details including shop, inventory, and reviews in a single API call."""
    # OPTIMIZATION: Fetch Bike, Inventory, and Shop in ONE single round-trip using SQL Joins
    result = db.query(Bike, BikeInventory, Shop)\
        .outerjoin(BikeInventory, BikeInventory.bike_id == Bike.id)\
        .outerjoin(Shop, Shop.id == Bike.shop_id)\
        .filter(Bike.id == bike_id)\
        .first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bike with ID {bike_id} not found"
        )
    
    bike, inventory, shop = result
    
    avail_dict = None
    if inventory:
        avail_dict = {
            "bike_id": bike_id,
            "is_available": inventory.available_quantity > 0,
            "available_count": inventory.available_quantity,
            "total_count": inventory.total_quantity
        }
        
    reviews = db.query(Review).filter(Review.shop_id == bike.shop_id).order_by(Review.created_at.desc()).limit(20).all() if bike.shop_id else []
    
    return {
        "vehicle": BikeOut.model_validate(bike),
        "availability": avail_dict,
        "shop": shop,
        "reviews": reviews
    }

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
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shop for this bike not found"
        )
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
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shop for this bike not found"
        )
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
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shop for this bike not found"
        )
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
        if file.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type: {file.content_type}. Only JPEG, PNG, and WebP are allowed."
            )
        
        if file.size and file.size > MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more files exceed the 5MB limit."
            )

        image_url = upload_image(file, folder=f"bikes/{bike_id}")
        image_url = optimize_cloudinary_url(image_url)
        db.add(BikeImage(bike_id=bike_id, image_url=image_url))

    db.commit()
    db.refresh(bike)
    return bike

@router.post("/{bike_id}/service-logs", response_model=ServiceLogOut, status_code=status.HTTP_201_CREATED)
def create_service_log(bike_id: int, log: ServiceLogCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new service log for a bike"""
    bike = db.query(Bike).filter(Bike.id == bike_id).first()
    if not bike:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bike not found")
        
    shop = db.query(Shop).filter(Shop.id == bike.shop_id).first()
    if not shop or shop.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
        
    db_log = ServiceLog(
        bike_id=bike_id,
        description=log.description,
        cost=log.cost,
        service_date=log.service_date
    )
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log

@router.get("/{bike_id}/service-logs", response_model=list[ServiceLogOut])
def get_service_logs(bike_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get service logs for a bike"""
    bike = db.query(Bike).filter(Bike.id == bike_id).first()
    if not bike:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bike not found")
        
    shop = db.query(Shop).filter(Shop.id == bike.shop_id).first()
    if not shop or shop.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
        
    return db.query(ServiceLog).filter(ServiceLog.bike_id == bike_id).order_by(ServiceLog.service_date.desc()).all()

@router.delete("/{bike_id}/service-logs/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service_log(bike_id: int, log_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a service log"""
    bike = db.query(Bike).filter(Bike.id == bike_id).first()
    if not bike:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bike not found")
        
    shop = db.query(Shop).filter(Shop.id == bike.shop_id).first()
    if not shop or shop.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
        
    log = db.query(ServiceLog).filter(ServiceLog.id == log_id, ServiceLog.bike_id == bike_id).first()
    if not log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service log not found")
        
    db.delete(log)
    db.commit()
