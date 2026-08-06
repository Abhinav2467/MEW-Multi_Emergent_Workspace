from pathlib import Path

import pytest

from resume_parser_agent.storage.database import connect, sqlite_path_from_url
from resume_parser_agent.storage.migrations import current_schema_version, initialize_database


def test_sqlite_path_from_url_handles_urls_and_paths() -> None:
    assert sqlite_path_from_url("sqlite+aiosqlite:///data/resume.db") == Path("data/resume.db")
    assert sqlite_path_from_url("sqlite:///data/resume.db") == Path("data/resume.db")
    assert sqlite_path_from_url("data/resume.db") == Path("data/resume.db")


@pytest.mark.asyncio
async def test_initialize_database_is_repeatable(tmp_path: Path) -> None:
    connection = await connect(f"sqlite+aiosqlite:///{tmp_path / 'resume.db'}")
    try:
        assert await current_schema_version(connection) is None

        await initialize_database(connection)
        await initialize_database(connection)

        assert await current_schema_version(connection) == 1
    finally:
        await connection.close()
