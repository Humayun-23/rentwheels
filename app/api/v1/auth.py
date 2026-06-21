from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm

from app.utils.limiter import limiter
from app.db.database import get_db
from app.db.models import User
from app.schemas.token import Token
from app.api.v1.oauth2 import create_access_token
from app.utils.utils import verify_password, hash_password
from pydantic import BaseModel
from google.oauth2 import id_token
from google.auth.transport import requests
import secrets
import os

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "647492306352-ajfb14t9be7ibq8furvfkb25rv3p6jql.apps.googleusercontent.com")

class GoogleLoginRequest(BaseModel):
    credential: str

router = APIRouter(tags=['Authentication'])


@router.post('/login', response_model=Token)
@limiter.limit("5/minute")
def login(request: Request, user_credentials: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login endpoint - returns JWT token"""
    user = db.query(User).filter(User.email == user_credentials.username).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Credentials")
    
    if not verify_password(user_credentials.password, user.password):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Credentials")

    if not user.is_email_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email not verified")

    access_token = create_access_token(data={"user_id": user.id, "role": "user"})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post('/google', response_model=Token)
@limiter.limit("5/minute")
def google_login(request: Request, body: GoogleLoginRequest, db: Session = Depends(get_db)):
    """Google OAuth Login endpoint"""
    try:
        idinfo = id_token.verify_oauth2_token(body.credential, requests.Request(), GOOGLE_CLIENT_ID)
        email = idinfo['email']
        firstname = idinfo.get('given_name', 'Google')
        lastname = idinfo.get('family_name', 'User')
        
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                email=email,
                password=hash_password(secrets.token_urlsafe(32)),
                firstname=firstname,
                lastname=lastname,
                phone_number="",
                user_type="customer",
                is_email_verified=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            
        if not user.is_email_verified:
            user.is_email_verified = True
            db.commit()

        access_token = create_access_token(data={"user_id": user.id, "role": "user"})
        return {"access_token": access_token, "token_type": "bearer"}
    except ValueError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Google Token")
