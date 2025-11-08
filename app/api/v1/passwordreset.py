from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import secrets

from app.db.database import get_db
from app.db.models import User, PasswordResetToken

from app.schemas.password_reset import (
    PasswordResetRequest,
    PasswordResetConfirm,
    PasswordResetResponse
)

from app.utils.utils import hash_password

router = APIRouter(prefix="/password-reset", tags=["password-reset"])


@router.post("/request", response_model=PasswordResetResponse, status_code=status.HTTP_200_OK)
def request_password_reset(reset_request: PasswordResetRequest, db: Session = Depends(get_db)):
    """
    Request a password reset token.
    In production, this should send an email with the reset link.
    For now, it returns the token in the response (for development/testing).
    """
    # Find user by email
    user = db.query(User).filter(User.email == reset_request.email).first()
    
    if not user:
        # For security, don't reveal if email exists or not
        return PasswordResetResponse(
            message="If the email exists, a password reset link has been sent."
        )
    
    # Invalidate any existing unused tokens for this user
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.is_used == False
    ).update({"is_used": True})
    
    # Generate a secure random token
    token = secrets.token_urlsafe(32)
    
    # Create password reset token (expires in 1 hour)
    reset_token = PasswordResetToken(
        user_id=user.id,
        token=token,
        expires_at=datetime.utcnow() + timedelta(hours=1)
    )
    
    db.add(reset_token)
    db.commit()
    
    # TODO: In production, send email with reset link
    # For now, return the token in the response (for development only)
    return PasswordResetResponse(
        message=f"Password reset token generated. Token: {token} (Valid for 1 hour. In production, this would be sent via email.)"
    )


@router.post("/confirm", response_model=PasswordResetResponse, status_code=status.HTTP_200_OK)
def confirm_password_reset(
    reset_confirm: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """
    Reset password using a valid token.
    """
    # Find the reset token
    reset_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == reset_confirm.token,
        PasswordResetToken.is_used == False
    ).first()
    
    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or already used reset token"
        )
    
    # Check if token has expired
    if reset_token.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired"
        )
    
    # Get the user
    user = db.query(User).filter(User.id == reset_token.user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update user password
    user.password = hash_password(reset_confirm.new_password)
    user.updated_at = datetime.utcnow()
    
    # Mark token as used
    reset_token.is_used = True
    
    db.commit()
    
    return PasswordResetResponse(
        message="Password has been successfully reset. You can now login with your new password."
    )