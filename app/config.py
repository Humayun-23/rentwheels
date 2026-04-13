import json
from pydantic import field_validator, ConfigDict
from pydantic_settings import BaseSettings

def parse_cors_origins_value(v):
    """Parse CORS origins from string or list format."""
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        # Accept JSON lists or comma-separated strings.
        raw = v.strip()
        if raw.startswith("[") and raw.endswith("]"):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass
        origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
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
    cors_origins: str | list[str] | None = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
    @field_validator("cors_origins", mode="before")
    @classmethod
    def _normalize_cors_origins(cls, v):
        return parse_cors_origins_value(v)
    environment: str = "production"  # or "staging", "production"
    debug: bool = True


settings = Settings()
