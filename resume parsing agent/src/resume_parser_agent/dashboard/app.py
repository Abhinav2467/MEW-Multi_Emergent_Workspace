"""FastAPI dashboard application factory."""

from pathlib import Path

from fastapi import FastAPI

from resume_parser_agent.config import Settings, get_settings
from resume_parser_agent.dashboard.events import DashboardEventBus
from resume_parser_agent.dashboard.routes import create_dashboard_router
from resume_parser_agent.errors import ConfigurationError
from resume_parser_agent.storage.repositories import ResumeRepository


PACKAGE_DIR = Path(__file__).resolve().parent


def build_dashboard_app(
    *,
    repository: ResumeRepository,
    settings: Settings | None = None,
    event_bus: DashboardEventBus | None = None,
) -> FastAPI:
    """Build the authenticated dashboard app."""

    resolved_settings = settings or get_settings()
    if not resolved_settings.dashboard_admin_password:
        raise ConfigurationError("DASHBOARD_ADMIN_PASSWORD is required for the dashboard.")

    app = FastAPI(title="Resume Parser Dashboard")
    app.state.repository = repository
    app.state.event_bus = event_bus or DashboardEventBus()

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/ready")
    async def ready():
        storage_ready = Path(resolved_settings.resume_storage_dir).exists()
        database_ready = await repository.health_check()
        return {
            "status": "ok" if storage_ready and database_ready else "not_ready",
            "storage": storage_ready,
            "database": database_ready,
        }

    app.include_router(
        create_dashboard_router(
            repository=repository,
            storage_dir=Path(resolved_settings.resume_storage_dir),
            event_bus=app.state.event_bus,
            admin_username=resolved_settings.dashboard_admin_username,
            admin_password=resolved_settings.dashboard_admin_password,
        )
    )
    return app
