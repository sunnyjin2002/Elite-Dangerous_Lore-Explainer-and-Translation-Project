"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the local MVP application."""

    app_name: str = "Elite Dangerous Translator"
    debug: bool = False
    log_level: str = "INFO"
    database_url: str = "sqlite:///./data/app.db"

    openai_api_key: str | None = None
    gemini_api_key: str | None = None
    deepseek_api_key: str | None = None

    wiki_username: str | None = None
    wiki_password: str | None = None

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None

    source_poll_url: str | None = None
    source_poll_interval_minutes: int = Field(default=30, ge=1)
    auto_publish_official_news: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    Path("data").mkdir(parents=True, exist_ok=True)
    return Settings()
