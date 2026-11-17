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

    # Local model (OpenAI-compatible endpoint, e.g. Ollama: http://localhost:11434/v1)
    LOCAL_MODEL_ENABLED: bool = False
    LOCAL_MODEL_BASE_URL: str = "http://localhost:11434/v1"
    LOCAL_MODEL_API_KEY: str = "ollama"
    LOCAL_MODEL_DEFAULT_MODEL: str = "llama3"

    # Online/OpenAI-compatible cloud model
    ONLINE_MODEL_ENABLED: bool = False
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str | None = None  # e.g. https://api.openai.com/v1 (leave None for default)
    OPENAI_DEFAULT_MODEL: str = "gpt-3.5-turbo"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
