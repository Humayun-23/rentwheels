from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from passlib.context import CryptContext
from typing import List

from app.api.v1.oauth2 import get_current_user, require_admin_token
from app.db.database import get_db
from app.db.models import User
from app.schemas.users import UserCreate, UserUpdate, UserOut
from app.utils import utils

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Create a new user (customer or shop_owner)"""
    try:
        # Check if email already exists
        existing_user = db.query(User).filter(User.email == user.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Hash the password (handles long passwords automatically)
        hashed_password = utils.hash_password(user.password)

        # Create new user with hashed password
        db_user = User(
            email=user.email,
            password=hashed_password,
            phone_number=user.phone_number,
            user_type=user.user_type,
        )

        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        return db_user

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error creating user. Email might already exist."
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{user_id}", response_model=UserOut)
def get_user_by_id(user_id: int, db: Session = Depends(get_db)):
    """Get a user by ID"""
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )

    return user


@router.put("/{user_id}", response_model=UserOut)
def update_user(user_id: int, user_update: UserUpdate, db: Session = Depends(get_db)):
    """Update a user's information (phone_number, shop)"""
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )

    # Update only provided fields
    if user_update.phone_number is not None:
        user.phone_number = user_update.phone_number

    try:
        db.commit()
        db.refresh(user)
        return user
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user: {str(e)}"
        )
        
        
@router.get("/", response_model=List[UserOut], include_in_schema=False)
def get_all_users(db: Session = Depends(get_db), _admin: bool = Depends(require_admin_token)):
    """Get all users (operator-only admin endpoint). Hidden from OpenAPI docs and protected by ADMIN_TOKEN."""
    users = db.query(User).all()
    return users
    