"""Repository layer for parsed resumes."""

from datetime import UTC, datetime
import hashlib
import json
from typing import Any

import aiosqlite

from resume_parser_agent.schemas import ParsedResume
from resume_parser_agent.storage.models import ResumeRecord


class ResumeRepository:
    """Async SQLite repository for parsed resumes."""

    def __init__(self, connection: aiosqlite.Connection) -> None:
        self._connection = connection

    async def create(
        self,
        *,
        telegram_user_id: int,
        parsed_resume: ParsedResume,
        original_filename: str,
        local_file_path: str,
        target_role: str | None = None,
        duplicate_status: str = "new",
        vector_indexing_status: str = "pending",
        version_number: int | None = None,
    ) -> ResumeRecord:
        """Insert a parsed resume and return the stored record."""

        person_name = parsed_resume.contact.name or "Unknown"
        resolved_version = version_number or await self.next_version(
            telegram_user_id=telegram_user_id,
            person_name=person_name,
            target_role=target_role,
        )
        text_hash = create_text_hash(parsed_resume.raw_text or "")
        payload = json.dumps(parsed_resume.model_dump(mode="json"), sort_keys=True)
        cursor = await self._connection.execute(
            """
            INSERT INTO parsed_resumes (
                telegram_user_id, person_name, target_role, parsed_json,
                version_number, duplicate_status, text_hash, vector_indexing_status,
                original_filename, local_file_path
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                telegram_user_id,
                person_name,
                target_role,
                payload,
                resolved_version,
                duplicate_status,
                text_hash,
                vector_indexing_status,
                original_filename,
                local_file_path,
            ),
        )
        await self._connection.commit()
        return await self.get(int(cursor.lastrowid))  # type: ignore[arg-type]

    async def get(self, record_id: int) -> ResumeRecord:
        """Fetch a parsed resume by ID."""

        cursor = await self._connection.execute(
            "SELECT * FROM parsed_resumes WHERE id = ?",
            (record_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            raise KeyError(f"parsed resume not found: {record_id}")
        return _record_from_row(row)

    async def list_for_user(self, telegram_user_id: int) -> list[ResumeRecord]:
        """List parsed resumes for one Telegram user, newest first."""

        cursor = await self._connection.execute(
            """
            SELECT * FROM parsed_resumes
            WHERE telegram_user_id = ?
            ORDER BY updated_at DESC, id DESC
            """,
            (telegram_user_id,),
        )
        rows = await cursor.fetchall()
        return [_record_from_row(row) for row in rows]

    async def list_all(self) -> list[ResumeRecord]:
        """List all parsed resumes, newest first."""

        cursor = await self._connection.execute(
            """
            SELECT * FROM parsed_resumes
            ORDER BY updated_at DESC, id DESC
            """
        )
        rows = await cursor.fetchall()
        return [_record_from_row(row) for row in rows]

    async def find_by_text_hash(
        self,
        *,
        telegram_user_id: int,
        text_hash: str,
    ) -> ResumeRecord | None:
        """Find an exact same-user text-hash match."""

        cursor = await self._connection.execute(
            """
            SELECT * FROM parsed_resumes
            WHERE telegram_user_id = ? AND text_hash = ?
            ORDER BY updated_at DESC, id DESC
            LIMIT 1
            """,
            (telegram_user_id, text_hash),
        )
        row = await cursor.fetchone()
        return _record_from_row(row) if row else None

    async def latest_for_person_role(
        self,
        *,
        telegram_user_id: int,
        person_name: str,
        target_role: str | None,
    ) -> ResumeRecord | None:
        """Return the latest version for a person and target role."""

        cursor = await self._connection.execute(
            """
            SELECT * FROM parsed_resumes
            WHERE telegram_user_id = ?
              AND person_name = ?
              AND (target_role IS ? OR target_role = ?)
            ORDER BY version_number DESC, updated_at DESC, id DESC
            LIMIT 1
            """,
            (telegram_user_id, person_name, target_role, target_role),
        )
        row = await cursor.fetchone()
        return _record_from_row(row) if row else None

    async def replace_latest_version(
        self,
        *,
        record_id: int,
        parsed_resume: ParsedResume,
        original_filename: str,
        local_file_path: str,
        duplicate_status: str = "updated",
        vector_indexing_status: str = "pending",
    ) -> ResumeRecord:
        """Replace the parsed JSON and file pointer for an existing latest version."""

        text_hash = create_text_hash(parsed_resume.raw_text or "")
        payload = json.dumps(parsed_resume.model_dump(mode="json"), sort_keys=True)
        await self._connection.execute(
            """
            UPDATE parsed_resumes
            SET parsed_json = ?,
                duplicate_status = ?,
                text_hash = ?,
                vector_indexing_status = ?,
                original_filename = ?,
                local_file_path = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                payload,
                duplicate_status,
                text_hash,
                vector_indexing_status,
                original_filename,
                local_file_path,
                record_id,
            ),
        )
        await self._connection.commit()
        return await self.get(record_id)

    async def next_version(
        self,
        *,
        telegram_user_id: int,
        person_name: str,
        target_role: str | None,
    ) -> int:
        """Return the next version number for a person and role."""

        latest = await self.latest_for_person_role(
            telegram_user_id=telegram_user_id,
            person_name=person_name,
            target_role=target_role,
        )
        return 1 if latest is None else latest.version_number + 1

    async def update_vector_indexing_status(
        self,
        record_id: int,
        status: str,
    ) -> ResumeRecord:
        """Update vector indexing status for a parsed resume."""

        await self._connection.execute(
            """
            UPDATE parsed_resumes
            SET vector_indexing_status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (status, record_id),
        )
        await self._connection.commit()
        return await self.get(record_id)

    async def list_pending_vector_indexes(self, limit: int = 50) -> list[ResumeRecord]:
        """List records that still need vector indexing."""

        cursor = await self._connection.execute(
            """
            SELECT * FROM parsed_resumes
            WHERE vector_indexing_status = 'pending'
            ORDER BY updated_at ASC, id ASC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cursor.fetchall()
        return [_record_from_row(row) for row in rows]

    async def delete(self, record_id: int) -> None:
        """Delete one parsed resume record."""

        await self._connection.execute(
            "DELETE FROM parsed_resumes WHERE id = ?",
            (record_id,),
        )
        await self._connection.commit()

    async def health_check(self) -> bool:
        """Return whether the repository can query SQLite."""

        cursor = await self._connection.execute("SELECT 1 AS ok")
        row = await cursor.fetchone()
        return bool(row and row["ok"] == 1)


def create_text_hash(text: str) -> str:
    """Create a stable hash for normalized resume text."""

    normalized = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _record_from_row(row: aiosqlite.Row) -> ResumeRecord:
    data: dict[str, Any] = dict(row)
    return ResumeRecord(
        id=int(data["id"]),
        telegram_user_id=int(data["telegram_user_id"]),
        person_name=str(data["person_name"]),
        target_role=data["target_role"],
        parsed_json=json.loads(str(data["parsed_json"])),
        version_number=int(data["version_number"]),
        duplicate_status=str(data["duplicate_status"]),
        text_hash=str(data["text_hash"]),
        vector_indexing_status=str(data["vector_indexing_status"]),
        original_filename=str(data["original_filename"]),
        local_file_path=str(data["local_file_path"]),
        created_at=_parse_datetime(str(data["created_at"])),
        updated_at=_parse_datetime(str(data["updated_at"])),
    )


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=UTC)
