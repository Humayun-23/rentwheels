from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Shop, User
from app.schemas.shops import ShopCreate, ShopUpdate, ShopOut
from app.api.v1.oauth2 import get_current_user

router = APIRouter(prefix="/shops", tags=["shops"])


@router.post("/", response_model=ShopOut, status_code=status.HTTP_201_CREATED)
def create_shop(shop: ShopCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new shop (only for shop_owner users)"""
    if current_user.user_type != "shop_owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shop owners can create shops"
        )

    db_shop = Shop(
        **shop.dict(),
        owner_id=current_user.id
    )
    db.add(db_shop)
    db.commit()
    db.refresh(db_shop)
    return db_shop


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
def get_all_shops(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all shops"""
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
    
    for key, value in shop_update.dict(exclude_unset=True).items():
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
