from pydantic import BaseModel

class GoogleLoginRequest(BaseModel):
    credential: str
    user_type: str = "customer"