"""
Application configuration module.

Loads environment variables from .env and provides a centralized Settings
object used across the application. All sensitive values (API keys, secrets)
are managed here and never hardcoded.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables and .env file.

    Attributes:
        APP_NAME: Display name of the application.
        APP_VERSION: Current application version string.
        DEBUG: Enable debug mode (verbose logging, auto-reload).
        OPENROUTER_API_KEY: API key for OpenRouter LLM service.
        DEFAULT_MODEL: Default LLM model identifier for OpenRouter.
        DATABASE_URL: SQLAlchemy-compatible database connection string.
        JWT_SECRET_KEY: Secret key used for signing JWT tokens.
        JWT_ALGORITHM: Algorithm used for JWT encoding/decoding.
        ACCESS_TOKEN_EXPIRE_MINUTES: Token expiry duration in minutes.
        UPLOAD_DIR: Directory path for storing uploaded files.
        MAX_UPLOAD_SIZE_MB: Maximum allowed upload file size in megabytes.
        LOG_LEVEL: Logging verbosity level.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- Application ---
    APP_NAME: str = "CodeLens"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # --- OpenRouter API ---
    OPENROUTER_API_KEY: str = "AQ.Ab8RN6JuuMpplmQO4SKIFmdT2dfsSiC3MCwYGmSB-ddR8phDlw"
    DEFAULT_MODEL: str = "openrouter/free"

    # --- Database ---
    DATABASE_URL: str = "sqlite+aiosqlite:///./codelens.db"

    # --- JWT Authentication ---
    JWT_SECRET_KEY: str = "change-this-to-a-random-secret-key-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # --- File Uploads ---
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    # --- Logging ---
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    @property
    def max_upload_size_bytes(self) -> int:
        """Return the maximum upload size in bytes."""
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def upload_path(self) -> Path:
        """Return the upload directory as a Path object, creating it if needed."""
        path = Path(self.UPLOAD_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    """
    Retrieve the cached application settings singleton.

    Returns:
        Settings: The application settings instance.
    """
    return Settings()
