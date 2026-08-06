"""SQLite schema bootstrap and migration helpers."""

import aiosqlite


SCHEMA_VERSION = 1


async def initialize_database(connection: aiosqlite.Connection) -> None:
    """Create the current schema if it does not exist."""

    await connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS parsed_resumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_user_id INTEGER NOT NULL,
            person_name TEXT NOT NULL,
            target_role TEXT,
            parsed_json TEXT NOT NULL,
            version_number INTEGER NOT NULL DEFAULT 1,
            duplicate_status TEXT NOT NULL DEFAULT 'new',
            text_hash TEXT NOT NULL,
            vector_indexing_status TEXT NOT NULL DEFAULT 'pending',
            original_filename TEXT NOT NULL,
            local_file_path TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_parsed_resumes_user_person_role
            ON parsed_resumes (telegram_user_id, person_name, target_role, version_number);

        CREATE INDEX IF NOT EXISTS idx_parsed_resumes_text_hash
            ON parsed_resumes (telegram_user_id, text_hash);
        """
    )
    await connection.execute(
        "INSERT OR IGNORE INTO schema_version (version) VALUES (?)",
        (SCHEMA_VERSION,),
    )
    await connection.commit()


async def current_schema_version(connection: aiosqlite.Connection) -> int | None:
    """Return the latest applied schema version, if initialized."""

    try:
        cursor = await connection.execute("SELECT MAX(version) AS version FROM schema_version")
    except aiosqlite.OperationalError:
        return None
    row = await cursor.fetchone()
    return int(row["version"]) if row and row["version"] is not None else None
