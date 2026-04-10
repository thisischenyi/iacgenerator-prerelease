import os
import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
from typing import List
from functools import lru_cache

# Calculate absolute database path
_backend_dir = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
_db_path = os.path.join(_backend_dir, "iac_generator.db")
_default_db_url = f"sqlite:///{_db_path}"

_INSECURE_SECRET_KEY = "change-this-to-a-secret-key-in-production"


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    # LLM Configuration
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    OPENAI_API_KEY: str = "your-api-key-here"
    OPENAI_MODEL_NAME: str = "gpt-4"
    OPENAI_TEMPERATURE: float = 0.7
    OPENAI_MAX_TOKENS: int = 4000

    # Database
    DATABASE_URL: str = _default_db_url

    # Security
    SECRET_KEY: str = _INSECURE_SECRET_KEY
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    FRONTEND_URL: str = "http://localhost:5173"

    # OAuth (Google/Microsoft)
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8666/api/auth/google/callback"

    MICROSOFT_CLIENT_ID: str = ""
    MICROSOFT_CLIENT_SECRET: str = ""
    MICROSOFT_TENANT_ID: str = "common"
    MICROSOFT_REDIRECT_URI: str = "http://localhost:8666/api/auth/microsoft/callback"

    # Application
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = False
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # File Upload
    MAX_UPLOAD_SIZE_MB: int = 10
    UPLOAD_DIR: str = "./uploads"

    @model_validator(mode="after")
    def validate_secret_key(self) -> "Settings":
        """Warn or fail if SECRET_KEY is the insecure default."""
        if self.SECRET_KEY == _INSECURE_SECRET_KEY:
            if not self.DEBUG:
                raise ValueError(
                    "SECRET_KEY must be changed from the default value in production "
                    "(set DEBUG=True to suppress this error in development)."
                )
            logging.warning(
                "SECRET_KEY is using the default insecure value. "
                "Set a strong SECRET_KEY in your .env file before deploying to production."
            )
        return self


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
