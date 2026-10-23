"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly typed application settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    log_level: str = "info"
    app_base_url: str = "http://localhost:8000"
    front_base_url: str = "http://localhost:3000"
    database_url: str = "sqlite+aiosqlite:///./dev.db"
    session_secret: str = "change-me-in-production"
    admin_email: str = "admin@example.com"
    admin_password_hash: str = ""
    llm_provider: str = "kilo"
    llm_model_extraction: str = "claude-haiku-4-5"
    llm_model_copywriting: str = "claude-sonnet-4-5"
    # Kilo AI (OpenAI-compatible gateway)
    kilo_api_url: str = "https://api.kilo.ai/v1"
    kilo_model: str = ""
    kilo_api_key: str = ""
    # Anthropic (supported option, requires API key)
    anthropic_api_key: str = ""
    llm_monthly_cap_usd: float = 20.0
    max_upload_mb: int = 5
    ssrf_max_redirects: int = 3


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()