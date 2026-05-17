from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from passlib.context import CryptContext
from typing import List
from datetime import timedelta
import os
import secrets
import smtplib
from email.message import EmailMessage
import logging

from app.api.v1.oauth2 import get_current_user, require_admin_token
from app.api.v1.oauth2 import create_access_token
from app.db.database import get_db
from app.db.models import User, EmailVerificationToken
from app.schemas.users import UserCreate, UserUpdate, UserOut
from app.schemas.email_verification import (
    EmailVerificationRequest,
    EmailVerificationResend,
    EmailVerificationResponse,
)
from app.utils import utils
from app.utils.limiter import limiter
from app.utils import tz

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def create_user(request: Request, user: UserCreate, db: Session = Depends(get_db)):
    """Create a new user (customer or shop_owner)"""
    try:
        normalized_email = user.email.strip().lower()
        # Check if email already exists
        existing_user = (
            db.query(User)
            .filter(func.lower(func.trim(User.email)) == normalized_email)
            .first()
        )
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Hash the password (handles long passwords automatically)
        hashed_password = utils.hash_password(user.password)

        # Create new user with hashed password
        db_user = User(
            email=normalized_email,
            password=hashed_password,
            firstname=user.firstname,
            lastname=user.lastname,
            phone_number=user.phone_number,
            user_type=user.user_type,
        )

        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        # Create verification token (expires in 24 hours)
        token = secrets.token_urlsafe(32)
        verification = EmailVerificationToken(
            user_id=db_user.id,
            token=token,
            expires_at=tz.now() + timedelta(hours=24),
        )
        db.add(verification)
        db.commit()

        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
        verify_link = f"{frontend_url}/verify-email?token={token}"

        smtp_host = os.getenv("SMTP_HOST")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")
        smtp_sender = os.getenv("SMTP_SENDER", smtp_user or "noreply@gopanda.in")

        if smtp_host and smtp_user and smtp_password:
            msg = EmailMessage()
            msg["Subject"] = "Verify your GoPanda account"
            msg["From"] = smtp_sender
            msg["To"] = db_user.email
            msg.set_content(
                "Welcome to GoPanda!\n\n"
                "Please verify your email address to activate your account:\n"
                f"{verify_link}\n\n"
                "This link expires in 24 hours."
            )

            try:
                with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_password)
                    server.send_message(msg)
            except Exception:
                logger.exception("Failed to send verification email")

        return db_user

    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error creating user: {exc.orig}"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/verify-email", response_model=EmailVerificationResponse, status_code=status.HTTP_200_OK)
def verify_email(payload: EmailVerificationRequest, db: Session = Depends(get_db)):
    """Verify email with a token."""
    token = db.query(EmailVerificationToken).filter(
        EmailVerificationToken.token == payload.token,
        EmailVerificationToken.is_used == False,
    ).first()

    if not token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")

    if tz.ensure_aware(token.expires_at) < tz.now():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification token has expired")

    user = db.query(User).filter(User.id == token.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.is_email_verified = True
    token.is_used = True
    db.commit()

    access_token = create_access_token(data={"user_id": user.id})
    return EmailVerificationResponse(
        message="Email verified successfully",
        access_token=access_token,
        token_type="bearer",
    )


@router.post("/verify-email/resend", response_model=EmailVerificationResponse, status_code=status.HTTP_200_OK)
@limiter.limit("1/30 seconds")
def resend_verification(request: Request, payload: EmailVerificationResend, db: Session = Depends(get_db)):
    """Resend verification email."""
    normalized_email = payload.email.strip().lower()
    user = db.query(User).filter(func.lower(func.trim(User.email)) == normalized_email).first()

    if not user:
        return EmailVerificationResponse(message="If the email exists, a verification link has been sent.")

    if user.is_email_verified:
        return EmailVerificationResponse(message="Email is already verified.")

    db.query(EmailVerificationToken).filter(
        EmailVerificationToken.user_id == user.id,
        EmailVerificationToken.is_used == False,
    ).update({"is_used": True})

    token = secrets.token_urlsafe(32)
    verification = EmailVerificationToken(
        user_id=user.id,
        token=token,
        expires_at=tz.now() + timedelta(hours=24),
    )
    db.add(verification)
    db.commit()

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
    verify_link = f"{frontend_url}/verify-email?token={token}"

    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_sender = os.getenv("SMTP_SENDER", smtp_user or "noreply@gopanda.in")

    if smtp_host and smtp_user and smtp_password:
        msg = EmailMessage()
        msg["Subject"] = "Verify your GoPanda account"
        msg["From"] = smtp_sender
        msg["To"] = user.email
        msg.set_content(
            "Please verify your email address to activate your account:\n"
            f"{verify_link}\n\n"
            "This link expires in 24 hours."
        )

        try:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
        except Exception:
            logger.exception("Failed to send verification email")

    return EmailVerificationResponse(message="If the email exists, a verification link has been sent.")


@router.get("/{user_id}", response_model=UserOut)
def get_user_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a user by ID"""
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )

    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own profile"
        )

    return user


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a user's information (phone_number, shop)"""
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )

    if current_user.id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own profile"
        )

    # Update only provided fields
    if user_update.firstname is not None:
        user.firstname = user_update.firstname
    if user_update.lastname is not None:
        user.lastname = user_update.lastname
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
def get_all_users(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
    db: Session = Depends(get_db), 
    _admin: bool = Depends(require_admin_token)
):
    """Get all users with pagination (operator-only admin endpoint). Hidden from OpenAPI docs and protected by ADMIN_TOKEN."""
    users = db.query(User).offset(skip).limit(limit).all()
    return users
    
