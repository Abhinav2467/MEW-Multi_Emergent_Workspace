"""Runtime entrypoints."""

import asyncio
from contextlib import suppress

import uvicorn

from resume_parser_agent.bot.app import build_application
from resume_parser_agent.config import get_settings
from resume_parser_agent.dashboard.app import build_dashboard_app
from resume_parser_agent.dashboard.events import DashboardEventBus
from resume_parser_agent.llm.gemini_client import GeminiCorrectionClient
from resume_parser_agent.logging_config import configure_logging
from resume_parser_agent.storage.database import connect
from resume_parser_agent.storage.migrations import initialize_database
from resume_parser_agent.storage.repositories import ResumeRepository
from resume_parser_agent.startup import validate_startup_settings
from resume_parser_agent.vectors.duplicate_detector import DuplicateDetector
from resume_parser_agent.vectors.embeddings import LocalEmbeddingProvider
from resume_parser_agent.vectors.qdrant_store import QdrantVectorStore


async def run_dashboard() -> None:
    """Run dashboard and, when configured, Telegram bot against shared storage."""

    settings = get_settings()
    configure_logging(settings.log_level)
    validate_startup_settings(settings, require_dashboard_password=True)
    connection = await connect(settings.database_url)
    try:
        await initialize_database(connection)
        repository = ResumeRepository(connection)
        event_bus = DashboardEventBus()
        app = build_dashboard_app(repository=repository, settings=settings, event_bus=event_bus)
        server = uvicorn.Server(
            uvicorn.Config(app, host="0.0.0.0", port=8000, log_level=settings.log_level.lower())
        )
        if settings.telegram_bot_token:
            embedding_provider = None
            vector_store = None
            if settings.enable_vector_dedup:
                embedding_provider = LocalEmbeddingProvider()
                vector_store = QdrantVectorStore(
                    url=settings.qdrant_url,
                    collection=settings.qdrant_collection,
                    vector_size=384,
                )
            duplicate_detector = DuplicateDetector(
                repository=repository,
                embedding_provider=embedding_provider,
                vector_store=vector_store,
            )
            correction_client = (
                GeminiCorrectionClient(api_key=settings.gemini_api_key, model=settings.gemini_model)
                if settings.gemini_api_key
                else None
            )
            telegram_app = build_application(
                settings,
                repository=repository,
                duplicate_detector=duplicate_detector,
                event_bus=event_bus,
                correction_client=correction_client,
            )
            await _serve_with_bot(server, telegram_app)
        else:
            await server.serve()
    finally:
        await connection.close()


async def _serve_with_bot(server: uvicorn.Server, telegram_app) -> None:
    """Run uvicorn and python-telegram-bot in the same event loop."""

    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.updater.start_polling()
    try:
        await server.serve()
    finally:
        await telegram_app.updater.stop()
        await telegram_app.stop()
        with suppress(Exception):
            await telegram_app.shutdown()


def main() -> None:
    """Run the dashboard entrypoint."""

    asyncio.run(run_dashboard())


if __name__ == "__main__":
    main()
