import os
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # Runtime
    ENVIRONMENT: str = "development"

    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "supertech_pm"

    # JWT
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    # Admin bootstrap password, used only before a password hash exists in DB.
    ADMIN_INITIAL_PASSWORD: str = "admin123"

    # Comma-separated origins. Use "*" only for local development.
    CORS_ORIGINS: str = "*"

    # Default Storage
    DEFAULT_STORAGE_PROVIDER: str = "aliyun"

    # Photo Sync
    PHOTO_SYNC_INTERVAL_MINUTES: int = 3
    PHOTO_SYNC_TIME_TOLERANCE_MINUTES: int = 5

    # Server
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in {"prod", "production"}

    @property
    def cors_origins(self) -> List[str]:
        origins = [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        return origins or ["*"]

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )

    @property
    def SYNC_DATABASE_URL(self) -> str:
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )

    class Config:
        env_file = BASE_DIR / ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
