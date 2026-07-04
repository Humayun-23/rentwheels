import json
from pydantic import ConfigDict, Field, field_validator
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
    algorithm: str = "HS256"

    @field_validator("algorithm", mode="before")
    @classmethod
    def validate_algorithm(cls, v):
        # Enforce HS256 to prevent JWT Algorithm Confusion attacks
        if v != "HS256":
            return "HS256"
        return v
    access_token_expire_minutes: int

    cors_origins: str = ""  # ← read as raw string, validator converts to list

    environment: str = "production"
    debug: bool = False

    cloudinary_url: str | None = Field(default=None, validation_alias="CLOUDINARY_URL")
    smtp_host: str | None = Field(default=None, validation_alias="SMTP_HOST")
    smtp_port: int = Field(default=587, validation_alias="SMTP_PORT")
    smtp_user: str | None = Field(default=None, validation_alias="SMTP_USER")
    smtp_password: str | None = Field(default=None, validation_alias="SMTP_PASSWORD")
    smtp_sender: str | None = Field(default=None, validation_alias="SMTP_SENDER")
    r2_account_id: str | None = Field(default=None, validation_alias="R2_ACCOUNT_ID")
    r2_access_key_id: str | None = Field(default=None, validation_alias="R2_ACCESS_KEY_ID")
    r2_secret_access_key: str | None = Field(default=None, validation_alias="R2_SECRET_ACCESS_KEY")
    r2_bucket_name: str | None = Field(default=None, validation_alias="R2_BUCKET_NAME")
    rentalos_max_upload_mb: int = Field(default=5, validation_alias="RENTALOS_MAX_UPLOAD_MB")
    rentalos_r2_presigned_expire_seconds: int = Field(default=900, validation_alias="RENTALOS_R2_PRESIGNED_EXPIRE_SECONDS")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, list):
            return ",".join(v)  # normalize back to string for consistency
        return v if isinstance(v, str) else ""

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, v):
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            normalized = v.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug"}:
                return True
            if normalized in {"0", "false", "no", "off", "release", "production"}:
                return False
        return v

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
