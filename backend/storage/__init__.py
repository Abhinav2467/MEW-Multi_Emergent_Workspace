"""SQLite database connection helpers."""

from __future__ import annotations

from pathlib import Path

import aiosqlite

from backend.config import get_settings


async def connect() -> aiosqlite.Connection:
    settings = get_settings()
    db_path = Path(settings.database_path)
    if db_path.is_dir():
        db_path = db_path / "app.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(str(db_path))
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA foreign_keys = ON")
    return conn


from fastapi import Request


async def get_db(request: Request):
    """FastAPI dependency yielding a DB connection, reusing request.state.db if already open."""
    if hasattr(request.state, "db") and request.state.db is not None:
        yield request.state.db
        return

    conn = await connect()
    request.state.db = conn
    try:
        yield conn
    finally:
        try:
            await conn.close()
        except Exception:
            pass
        request.state.db = None
