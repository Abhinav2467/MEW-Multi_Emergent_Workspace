"""Typed application settings."""

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed settings for the resume parser agent."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "local"
    log_level: str = "INFO"

    parser_latency_budget_ms: Annotated[int, Field(gt=0)] = 300
    resume_storage_dir: Path = Path("data/resumes")

    telegram_bot_token: str | None = None
    telegram_allowed_chat_ids: Annotated[tuple[int, ...], NoDecode] = ()

    dashboard_admin_username: str = "admin"
    dashboard_admin_password: str | None = None

    database_url: str = "sqlite+aiosqlite:///data/resume_parser.db"
    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection: str = "resumes"
    enable_vector_dedup: bool = False

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    enable_llm_fallback: bool = False

    @field_validator("telegram_allowed_chat_ids", mode="before")
    @classmethod
    def parse_chat_ids(cls, value: object) -> tuple[int, ...]:
        """Parse comma-separated Telegram chat IDs from environment variables."""

        if value is None or value == "":
            return ()
        if isinstance(value, str):
            return tuple(int(item.strip()) for item in value.split(",") if item.strip())
        if isinstance(value, (list, tuple, set)):
            return tuple(int(item) for item in value)
        raise TypeError("telegram_allowed_chat_ids must be a CSV string or sequence")

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        return value.upper()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()
