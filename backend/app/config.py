"""Application configuration, loaded from environment / repo-root .env."""

from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# config.py lives at backend/app/config.py -> repo root is two levels up.
REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env")


class Settings(BaseSettings):
    app_name: str = "Kabadi Mitra API"
    app_env: str = "development"
    log_level: str = "INFO"

    database_url: str = ""
    supabase_url: str = ""
    supabase_jwks_url: str = ""

    jwt_audience: str = "authenticated"
    jwt_issuer_suffix: str = "/auth/v1"

    # Cloudinary
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""

    # Redis (reserved; rate limiting / jobs)
    redis_url: str = ""

    # AI (pluggable; assistive only)
    ai_provider: str = "none"
    ai_api_key: str = ""
    ai_model: str = ""
    ai_base_url: str = ""
    ai_confidence_threshold: float = 0.80
    ai_review_threshold: float = 0.50
    ai_timeout_seconds: float = 30.0
    ai_zdr: bool = True

    # Frontend
    frontend_url: str = ""

    # CORS (comma-separated allowed origins for browser clients)
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8081",
        validation_alias="BACKEND_CORS_ORIGINS",
    )

    # Rate limiting (in-memory; per client IP)
    rate_limit: int = 1000
    rate_limit_window_seconds: int = 60

    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")


settings = Settings()
