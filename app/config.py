from pydantic_settings import BaseSettings

class Settings(BaseSettings):
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

    class Config:
        env_file = ".env"


settings = Settings()