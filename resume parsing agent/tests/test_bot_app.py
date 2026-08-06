import pytest

from resume_parser_agent.bot.app import build_application
from resume_parser_agent.config import Settings
from resume_parser_agent.errors import ConfigurationError


def test_build_application_requires_token() -> None:
    with pytest.raises(ConfigurationError):
        build_application(Settings(telegram_bot_token=None, _env_file=None))


def test_build_application_wires_dependencies() -> None:
    app = build_application(
        Settings(
            telegram_bot_token="123:fake",
            telegram_allowed_chat_ids="123",
            _env_file=None,
        )
    )

    assert "dependencies" in app.bot_data
    assert app.bot_data["dependencies"].allowed_chat_ids == (123,)
