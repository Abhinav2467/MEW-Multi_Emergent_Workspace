"""Startup validation helpers."""

from resume_parser_agent.config import Settings
from resume_parser_agent.errors import ConfigurationError


def validate_startup_settings(
    settings: Settings,
    *,
    require_dashboard_password: bool = False,
) -> None:
    """Validate config that should fail fast at service startup."""

    settings.resume_storage_dir.mkdir(parents=True, exist_ok=True)
    if require_dashboard_password and not settings.dashboard_admin_password:
        raise ConfigurationError("DASHBOARD_ADMIN_PASSWORD is required.")
    if settings.enable_llm_fallback and not settings.gemini_api_key:
        raise ConfigurationError("GEMINI_API_KEY is required when ENABLE_LLM_FALLBACK=true.")
