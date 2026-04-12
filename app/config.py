from pydantic import field_validator, ConfigDict
from pydantic_settings import BaseSettings
from typing import Annotated
from pydantic import BeforeValidator

def parse_cors_origins_value(v):
    """Parse CORS origins from string or list format"""
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        # Split by comma and strip whitespace from each origin
        origins = [origin.strip() for origin in v.split(",") if origin.strip()]
        return origins if origins else None
    return v

class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", extra="ignore")
    
    database_hostname: str
    database_port: str
    database_password: str
    database_name: str
    database_username: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    # Admin token used to protect operator-only endpoints. Set this in your environment.
    admin_token: str | None = None
    # Comma-separated list of IPs allowed to call admin endpoints (defaults to localhost)
    admin_allowed_hosts: str = "127.0.0.1,::1"
    cors_origins: Annotated[list[str], BeforeValidator(parse_cors_origins_value)] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
    environment: str = "development"  # or "staging", "production"
    debug: bool = True


settings = Settings()
