"""Environment-driven application settings (clean layered backend).

Secrets are read from environment variables / a git-ignored ``.env`` file and
are never hard-coded (FR-059).
"""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# app/core/config.py -> repo root is three levels up.
REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_name: str = "Kabadi Mitra API"
    app_env: str = "development"
    log_level: str = "INFO"

    database_url: str = ""

    # Supabase (project + auth)
    supabase_url: str = ""
    supabase_jwks_url: str = ""

    # AUTH (Supabase JWT verification)
    jwt_audience: str = "authenticated"
    jwt_issuer_suffix: str = "/auth/v1"

    # Cloudinary (media)
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""

    # Redis (cache / jobs)
    redis_url: str = ""

    # AI (pluggable, assistive only)
    ai_provider: str = "none"
    ai_api_key: str = ""
    ai_model: str = ""
    ai_base_url: str = ""
    ai_confidence_threshold: float = 0.80
    ai_review_threshold: float = 0.50

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

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
