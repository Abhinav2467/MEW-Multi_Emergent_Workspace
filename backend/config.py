"""Application settings loaded from environment variables."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = BACKEND_DIR.parent

# Same out-of-band redirect used by cold_email_agent for installed (Desktop) clients
OOB_REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"


class GoogleOAuthClient(NamedTuple):
    client_id: str
    client_secret: str
    redirect_uri: str
    source: str


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[str(WORKSPACE_DIR / ".env"), str(BACKEND_DIR / ".env")],
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Auth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/callback"
    google_credentials_path: str = str(
        WORKSPACE_DIR / "cold_email_agent" / "credentials.json"
    )
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 72

    # LLM / search APIs
    gemini_api_key: str = ""
    google_api_key: str = ""  # alias accepted by google-genai; used if gemini_api_key empty
    gemini_parser_key: str = ""  # Dedicated key for MEW_RESUME_PARSER
    gemini_email_key: str = ""   # Dedicated key for MEW_COLD_EMAIL_STUDIO
    gemini_backup_key: str = ""  # Emergency backup key MEW_LLM_FAILOVER
    gemini_model: str = "gemini-1.5-flash"
    groq_api_key: str = ""
    tavily_api_key: str = ""
    hunter_api_key: str = ""

    # Paths
    database_path: str = str(BACKEND_DIR / "data" / "app.db")
    reports_dir: str = str(BACKEND_DIR / "reports")
    resumes_dir: str = str(BACKEND_DIR / "data" / "resumes")

    # App
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173"
    careerzenith_api_base: str = "https://api.careerzenith.ai/job-board/user/"
    top_job_matches: int = 15
    job_recency_days: int = 22
    email_draft_concurrency: int = 3
    link_check_concurrency: int = 10
    link_check_timeout_seconds: float = 5.0

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def resolved_parser_gemini_key(self) -> str:
        """Dedicated parser key -> backup key -> primary key -> google api key."""
        return (self.gemini_parser_key or self.gemini_backup_key or self.gemini_api_key or self.google_api_key or "").strip()

    @property
    def resolved_email_gemini_key(self) -> str:
        """Dedicated cold email key -> backup key -> primary key -> google api key."""
        return (self.gemini_email_key or self.gemini_backup_key or self.gemini_api_key or self.google_api_key or "").strip()

    @property
    def resolved_gemini_api_key(self) -> str:
        """General fallback resolution across all available keys."""
        return (self.gemini_parser_key or self.gemini_email_key or self.gemini_backup_key or self.gemini_api_key or self.google_api_key or "").strip()


@lru_cache
def get_settings() -> Settings:
    return Settings()


def _load_client_from_credentials_file(path: Path) -> tuple[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    block = data.get("installed") or data.get("web")
    if not isinstance(block, dict):
        raise ValueError(
            f"Invalid Google credentials file (expected 'installed' or 'web' key): {path}"
        )
    client_id = (block.get("client_id") or "").strip()
    client_secret = (block.get("client_secret") or "").strip()
    if not client_id or not client_secret:
        raise ValueError(f"credentials file missing client_id/client_secret: {path}")
    return client_id, client_secret


def resolve_google_oauth_client() -> GoogleOAuthClient:
    """Resolve Google OAuth client from env, else cold_email_agent/credentials.json."""
    settings = get_settings()

    env_id = settings.google_client_id.strip()
    env_secret = settings.google_client_secret.strip()
    if env_id and env_secret:
        return GoogleOAuthClient(
            client_id=env_id,
            client_secret=env_secret,
            redirect_uri=settings.google_redirect_uri,
            source="env",
        )

    creds_path = Path(settings.google_credentials_path)
    if creds_path.is_file():
        client_id, client_secret = _load_client_from_credentials_file(creds_path)
        return GoogleOAuthClient(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=settings.google_redirect_uri or "http://localhost",
            source=str(creds_path),
        )

    raise ValueError(
        "Google OAuth is not configured. Either set GOOGLE_CLIENT_ID and "
        "GOOGLE_CLIENT_SECRET in backend/.env, or place a Desktop OAuth client "
        f"file at {creds_path} (same as cold_email_agent/credentials.json)."
    )
