import pytest
from pydantic import ValidationError

from resume_parser_agent.config import Settings, get_settings


def test_settings_parse_chat_ids_and_normalize_log_level() -> None:
    settings = Settings(
        telegram_allowed_chat_ids="123, 456",
        log_level="debug",
        _env_file=None,
    )

    assert settings.telegram_allowed_chat_ids == (123, 456)
    assert settings.log_level == "DEBUG"


def test_settings_empty_chat_ids_allow_everyone() -> None:
    settings = Settings(telegram_allowed_chat_ids="", _env_file=None)

    assert settings.telegram_allowed_chat_ids == ()


def test_settings_reject_invalid_latency_budget() -> None:
    with pytest.raises(ValidationError):
        Settings(parser_latency_budget_ms=0, _env_file=None)


def test_get_settings_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("LOG_LEVEL", "warning")

    first = get_settings()
    second = get_settings()

    assert first is second
    assert first.log_level == "WARNING"

    get_settings.cache_clear()
