import json
from pydantic import ConfigDict, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file=".env",
        extra="ignore",
        env_parse_none_str="None",
    )

    database_hostname: str
    database_port: str
    database_password: str
    database_name: str
    database_username: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int

    admin_token: str | None = None
    admin_allowed_hosts: str = "127.0.0.1,::1"
    cors_origins: str = ""  # ← read as raw string, validator converts to list

    environment: str = "production"
    debug: bool = False

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, list):
            return ",".join(v)  # normalize back to string for consistency
        return v if isinstance(v, str) else ""

    def get_cors_origins(self) -> list[str]:
        if not self.cors_origins.strip():
            return []
        try:
            parsed = json.loads(self.cors_origins)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()