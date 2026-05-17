from pydantic import BaseModel, EmailStr


class EmailVerificationRequest(BaseModel):
    token: str


class EmailVerificationResend(BaseModel):
    email: EmailStr


class EmailVerificationResponse(BaseModel):
    message: str
