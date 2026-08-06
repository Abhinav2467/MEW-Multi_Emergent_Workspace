"""SQLite connection helpers."""

from pathlib import Path
from urllib.parse import unquote

import aiosqlite


def sqlite_path_from_url(database_url: str) -> Path:
    """Extract a filesystem path from a SQLite URL or plain path."""

    prefixes = ("sqlite+aiosqlite:///", "sqlite:///")
    for prefix in prefixes:
        if database_url.startswith(prefix):
            return Path(unquote(database_url.removeprefix(prefix)))
    return Path(database_url)


async def connect(database_url: str) -> aiosqlite.Connection:
    """Open a SQLite connection configured for row dictionaries and FK checks."""

    path = sqlite_path_from_url(database_url)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = await aiosqlite.connect(path)
    connection.row_factory = aiosqlite.Row
    await connection.execute("PRAGMA foreign_keys = ON")
    return connection
