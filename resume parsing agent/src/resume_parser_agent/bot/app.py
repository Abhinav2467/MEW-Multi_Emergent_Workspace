"""Telegram application factory."""

from pathlib import Path

from telegram.ext import Application, CommandHandler, MessageHandler, filters

from resume_parser_agent.bot.handlers import (
    BotDependencies,
    handle_confirmation,
    handle_correction_message,
    handle_error,
    handle_resume_upload,
    handle_start,
)
from resume_parser_agent.bot.session_store import SessionStore
from resume_parser_agent.config import Settings, get_settings
from resume_parser_agent.dashboard.events import DashboardEventBus
from resume_parser_agent.errors import ConfigurationError
from resume_parser_agent.llm.gemini_client import GeminiCorrectionClient
from resume_parser_agent.parser.service import ResumeParserService
from resume_parser_agent.storage.repositories import ResumeRepository
from resume_parser_agent.vectors.duplicate_detector import DuplicateDetector


def build_application(
    settings: Settings | None = None,
    *,
    repository: ResumeRepository | None = None,
    duplicate_detector: DuplicateDetector | None = None,
    event_bus: DashboardEventBus | None = None,
    correction_client: GeminiCorrectionClient | None = None,
) -> Application:
    """Build the python-telegram-bot application."""

    resolved_settings = settings or get_settings()
    if not resolved_settings.telegram_bot_token:
        raise ConfigurationError("TELEGRAM_BOT_TOKEN is required to start the bot.")

    application = Application.builder().token(resolved_settings.telegram_bot_token).build()
    application.bot_data["dependencies"] = BotDependencies(
        parser_service=ResumeParserService(),
        session_store=SessionStore(),
        storage_dir=Path(resolved_settings.resume_storage_dir),
        allowed_chat_ids=resolved_settings.telegram_allowed_chat_ids,
        repository=repository,
        duplicate_detector=duplicate_detector,
        event_bus=event_bus,
        correction_client=correction_client,
    )

    application.add_handler(CommandHandler("start", handle_start))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_resume_upload))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_confirmation))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_correction_message))
    application.add_error_handler(handle_error)
    return application


def run_bot(settings: Settings | None = None) -> None:
    """Run the Telegram bot using long polling."""

    build_application(settings).run_polling()
