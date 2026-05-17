from pydantic import BaseModel, EmailStr
from typing import Optional


class EmailVerificationRequest(BaseModel):
    token: str


class EmailVerificationResend(BaseModel):
    email: EmailStr


class EmailVerificationResponse(BaseModel):
    message: str
    access_token: Optional[str] = None
    token_type: Optional[str] = None
