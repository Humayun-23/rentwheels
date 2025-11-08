from datetime import datetime
from app.db.database import get_db
from app.schemas.reviews import ReviewCreate, ReviewOut, ReviewUpdate
from app.api.v1.oauth2 import get_current_user
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.db.models import Booking, User, Bike, Review


router = APIRouter(prefix="/shops", tags=["reviews"]) 



@router.post("/{shop_id}/reviews", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
def create_review(shop_id: int, review: ReviewCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new review for a shop by a customer"""
    if current_user.user_type != "customer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only customers can create reviews"
        )
        
    # Verify that the customer has completed a booking with the shop
    has_completed = (
    db.query(Booking.id)
    .join(Bike, Booking.bike_id == Bike.id)
    .filter(
        Booking.customer_id == current_user.id,
        Booking.status == "completed",
        Bike.shop_id == shop_id,  
    )
    .first()
    is not None
    )
    if not has_completed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only review shops you have completed a booking with"
        )
    existing = db.query(Review).filter(Review.customer_id == current_user.id, Review.shop_id == shop_id).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You have already reviewed this shop")

    db_review = Review(
        customer_id=current_user.id,
        shop_id=shop_id,
        rating=review.rating,
        comment=review.comment,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    return db_review

@router.get("/{shop_id}/reviews", response_model=list[ReviewOut])
def get_shop_reviews(
    shop_id: int, 
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    """Get all reviews for a shop with pagination"""
    reviews = db.query(Review).filter(
        Review.shop_id == shop_id
    ).offset(skip).limit(limit).all()
    return reviews

@router.put("/{shop_id}/reviews/{review_id}", response_model=ReviewOut)
def update_review(shop_id: int, review_id: int, review_update: ReviewUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update a review for a shop by the customer who created it"""
    review = db.query(Review).filter(Review.id == review_id, Review.shop_id == shop_id).first()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )

    if review.customer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own reviews"
        )

    # Apply partial updates
    if review_update.rating is not None:
        review.rating = review_update.rating
    if review_update.comment is not None:
        review.comment = review_update.comment

    review.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(review)
    return review


@router.delete("/{shop_id}/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review(shop_id: int, review_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a review created by the current customer"""
    review = db.query(Review).filter(Review.id == review_id, Review.shop_id == shop_id).first()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )

    if review.customer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own reviews"
        )

    db.delete(review)
    db.commit()
    return None
