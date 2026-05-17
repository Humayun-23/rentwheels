from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta
from app.utils import tz
import logging
import os
import secrets
import smtplib
from email.message import EmailMessage

from app.db.database import get_db
from app.db.models import User, PasswordResetToken

from app.schemas.password_reset import (
    PasswordResetRequest,
    PasswordResetConfirm,
    PasswordResetResponse
)

from app.utils.utils import hash_password

router = APIRouter(prefix="/password-reset", tags=["password-reset"])
logger = logging.getLogger(__name__)


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
        expires_at=tz.now() + timedelta(hours=1)
    )

    db.add(reset_token)
    db.commit()

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")
    reset_link = f"{frontend_url}/reset-password?token={token}"

    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_sender = os.getenv("SMTP_SENDER", smtp_user or "noreply@ridewheel.com")

    if smtp_host and smtp_user and smtp_password:
        msg = EmailMessage()
        msg["Subject"] = "RideWheel password reset"
        msg["From"] = smtp_sender
        msg["To"] = user.email
        msg.set_content(
            "We received a request to reset your password. "
            f"Use this link to continue: {reset_link}\n\n"
            "This link expires in 1 hour."
        )

        try:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
        except Exception:
            logger.exception("Failed to send password reset email")

    return PasswordResetResponse(
        message="If the email exists, a password reset link has been sent."
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
    if reset_token.expires_at < tz.now():
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
    user.updated_at = tz.now()

    # Mark token as used
    reset_token.is_used = True
    db.commit()  # ✅ FIXED: Ensure changes are persisted

    return PasswordResetResponse(
        message="Password has been successfully reset. You can now login with your new password."
    )
