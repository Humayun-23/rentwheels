from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Shop, User, ShopImage
from app.schemas.shops import ShopCreate, ShopUpdate, ShopOut
from app.api.v1.oauth2 import get_current_user
from app.utils.cloudinary_client import upload_image

router = APIRouter(prefix="/shops", tags=["shops"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB

@router.post("/", response_model=ShopOut, status_code=status.HTTP_201_CREATED)
def create_shop(shop: ShopCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new shop (only for shop_owner users)"""
    if current_user.user_type != "shop_owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shop owners can create shops"
        )

    db_shop = Shop(
        **shop.model_dump(exclude_unset=True),  # ✅ FIXED: Pydantic v2
        owner_id=current_user.id
    )
    db.add(db_shop)
    db.commit()
    db.refresh(db_shop)
    return db_shop


@router.get("/me", response_model=list[ShopOut])
def get_my_shops(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get shops owned by the current user"""
    if current_user.user_type != "shop_owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shop owners can access their shops"
        )

    shops = (
        db.query(Shop)
        .filter(Shop.owner_id == current_user.id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return shops


@router.get("/{shop_id}", response_model=ShopOut)
def get_shop(shop_id: int, db: Session = Depends(get_db)):
    """Get a shop by ID"""
    shop = db.query(Shop).filter(Shop.id == shop_id).first()
    
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shop with ID {shop_id} not found"
        )
    
    return shop


@router.get("/", response_model=list[ShopOut])
def get_all_shops(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    """Get all shops with pagination"""
    shops = db.query(Shop).offset(skip).limit(limit).all()
    return shops


@router.put("/{shop_id}", response_model=ShopOut)
def update_shop(shop_id: int, shop_update: ShopUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update a shop (only owner can update)"""
    shop = db.query(Shop).filter(Shop.id == shop_id).first()
    
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shop with ID {shop_id} not found"
        )
    
    if shop.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own shop"
        )
    
    for key, value in shop_update.model_dump(exclude_unset=True).items():  # ✅ FIXED: Pydantic v2
        setattr(shop, key, value)
    
    db.commit()
    db.refresh(shop)
    return shop


@router.delete("/{shop_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shop(shop_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a shop (only owner can delete)"""
    shop = db.query(Shop).filter(Shop.id == shop_id).first()
    
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shop with ID {shop_id} not found"
        )
    
    if shop.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own shop"
        )
    
    db.delete(shop)
    db.commit()


@router.post("/{shop_id}/image", response_model=ShopOut)
def upload_shop_image(
    shop_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload or replace a single shop image"""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type: {file.content_type}. Only JPEG, PNG, and WebP are allowed."
        )

    if file.size and file.size > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds the 5MB limit."
        )

    shop = db.query(Shop).filter(Shop.id == shop_id).first()
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shop with ID {shop_id} not found",
        )

    if shop.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own shop",
        )

    image_url = upload_image(file, folder=f"shops/{shop_id}")

    existing = db.query(ShopImage).filter(ShopImage.shop_id == shop_id).first()
    if existing:
        existing.image_url = image_url
    else:
        db.add(ShopImage(shop_id=shop_id, image_url=image_url))

    db.commit()
    db.refresh(shop)
    return shop
