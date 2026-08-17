"""SQLite database connection helpers."""

from __future__ import annotations

from pathlib import Path

import aiosqlite

from backend.config import get_settings


async def connect() -> aiosqlite.Connection:
    settings = get_settings()
    db_path = Path(settings.database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(str(db_path))
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA foreign_keys = ON")
    return conn


async def get_db():
    """FastAPI dependency yielding a DB connection."""
    conn = await connect()
    try:
        yield conn
        await conn.commit()
    finally:
        await conn.close()
