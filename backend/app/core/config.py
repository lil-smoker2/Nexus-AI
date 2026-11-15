"""Pydantic settings for NEXUS AI backend."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "NEXUS AI"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "tauri://localhost"]
    SECRET_KEY: str = "dev-secret-change-in-production"
    DATABASE_URL: str = "sqlite:///./nexus_ai.db"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
