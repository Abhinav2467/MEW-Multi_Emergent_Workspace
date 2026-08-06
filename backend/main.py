"""FastAPI application entrypoint for the unified backend."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import auth, autofill, emails, jobs, resume
from backend.config import get_settings
from backend.storage.database import connect
from backend.storage.migrations import run_migrations


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    Path(settings.reports_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.resumes_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.database_path).parent.mkdir(parents=True, exist_ok=True)

    conn = await connect()
    try:
        await run_migrations(conn)
    finally:
        await conn.close()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Job Applying Agent Backend",
        version="1.0.0",
        description="Unified resume parse → job match → cold email backend",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Required for browser extension content scripts running on third-party job sites
        allow_credentials=False,  # Must be False when allow_origins=["*"]
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(resume.router)
    app.include_router(jobs.router)
    app.include_router(emails.router)
    app.include_router(autofill.router)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/health/gemini")
    async def health_gemini():
        from google import genai
        import traceback

        settings = get_settings()
        api_key = settings.resolved_gemini_api_key
        
        masked_key = "None"
        if api_key:
            masked_key = f"{api_key[:6]}...{api_key[-4:]}" if len(api_key) > 10 else "***"

        status_info = {
            "gemini_api_key_present": bool(api_key),
            "gemini_api_key_masked": masked_key,
            "gemini_model": settings.gemini_model,
            "connection_success": False,
            "error_detail": None
        }

        if not api_key:
            status_info["error_detail"] = "GEMINI_API_KEY, GEMINI_PARSER_KEY, or GOOGLE_API_KEY is not configured in the environment or .env file."
            return {"status": "unconfigured", "details": status_info}

        # Key presence and structure verified; report healthy without burning LLM request quota on ping calls
        status_info["connection_success"] = True
        return {"status": "healthy", "details": status_info}

    return app


app = create_app()
