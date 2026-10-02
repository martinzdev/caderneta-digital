from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./caderneta.db"
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    max_login_attempts: int = 5
    lockout_minutes: int = 15
    cors_origins: list[str] = ["http://localhost:4200"]
    secure_cookies: bool = False
    enable_docs: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
