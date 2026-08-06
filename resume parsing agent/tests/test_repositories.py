from pathlib import Path

import pytest

from resume_parser_agent.schemas import ContactInfo, ParsedResume
from resume_parser_agent.storage.database import connect
from resume_parser_agent.storage.migrations import initialize_database
from resume_parser_agent.storage.repositories import ResumeRepository, create_text_hash


def parsed_resume(name: str = "Jane Doe", raw_text: str = "Jane Doe\nPython") -> ParsedResume:
    return ParsedResume(
        contact=ContactInfo(name=name, email="jane@example.com"),
        skills=["Python"],
        raw_text=raw_text,
    )


@pytest.mark.asyncio
async def test_create_and_fetch_parsed_resume(tmp_path: Path) -> None:
    connection = await connect(f"sqlite+aiosqlite:///{tmp_path / 'resume.db'}")
    try:
        await initialize_database(connection)
        repository = ResumeRepository(connection)

        record = await repository.create(
            telegram_user_id=123,
            parsed_resume=parsed_resume(),
            original_filename="upload.pdf",
            local_file_path="Jane_Doe__abc.pdf",
            target_role="Backend Engineer",
        )

        fetched = await repository.get(record.id)

        assert fetched.person_name == "Jane Doe"
        assert fetched.parsed_json["contact"]["email"] == "jane@example.com"
        assert fetched.local_file_path == "Jane_Doe__abc.pdf"
        assert fetched.version_number == 1
        assert fetched.vector_indexing_status == "pending"
    finally:
        await connection.close()


@pytest.mark.asyncio
async def test_resume_versions_are_tracked(tmp_path: Path) -> None:
    connection = await connect(f"sqlite+aiosqlite:///{tmp_path / 'resume.db'}")
    try:
        await initialize_database(connection)
        repository = ResumeRepository(connection)

        first = await repository.create(
            telegram_user_id=123,
            parsed_resume=parsed_resume(),
            original_filename="one.pdf",
            local_file_path="one.pdf",
            target_role="Backend",
        )
        second = await repository.create(
            telegram_user_id=123,
            parsed_resume=parsed_resume(raw_text="Jane Doe\nFastAPI"),
            original_filename="two.pdf",
            local_file_path="two.pdf",
            target_role="Backend",
        )

        assert first.version_number == 1
        assert second.version_number == 2
        assert (await repository.latest_for_person_role(
            telegram_user_id=123,
            person_name="Jane Doe",
            target_role="Backend",
        )).id == second.id
    finally:
        await connection.close()


@pytest.mark.asyncio
async def test_replace_latest_version_updates_json_and_file_path(tmp_path: Path) -> None:
    connection = await connect(f"sqlite+aiosqlite:///{tmp_path / 'resume.db'}")
    try:
        await initialize_database(connection)
        repository = ResumeRepository(connection)
        record = await repository.create(
            telegram_user_id=123,
            parsed_resume=parsed_resume(),
            original_filename="old.pdf",
            local_file_path="old.pdf",
        )

        updated = await repository.replace_latest_version(
            record_id=record.id,
            parsed_resume=parsed_resume(raw_text="Jane Doe\nDocker"),
            original_filename="new.pdf",
            local_file_path="new.pdf",
        )

        assert updated.id == record.id
        assert updated.version_number == 1
        assert updated.local_file_path == "new.pdf"
        assert updated.duplicate_status == "updated"
        assert updated.text_hash == create_text_hash("Jane Doe\nDocker")
    finally:
        await connection.close()


@pytest.mark.asyncio
async def test_list_and_find_by_text_hash_are_user_scoped(tmp_path: Path) -> None:
    connection = await connect(f"sqlite+aiosqlite:///{tmp_path / 'resume.db'}")
    try:
        await initialize_database(connection)
        repository = ResumeRepository(connection)
        record = await repository.create(
            telegram_user_id=123,
            parsed_resume=parsed_resume(raw_text="same resume"),
            original_filename="one.pdf",
            local_file_path="one.pdf",
        )
        await repository.create(
            telegram_user_id=999,
            parsed_resume=parsed_resume(raw_text="same resume"),
            original_filename="two.pdf",
            local_file_path="two.pdf",
        )

        assert [item.id for item in await repository.list_for_user(123)] == [record.id]
        match = await repository.find_by_text_hash(
            telegram_user_id=123,
            text_hash=create_text_hash("same resume"),
        )
        other_user_match = await repository.find_by_text_hash(
            telegram_user_id=456,
            text_hash=create_text_hash("same resume"),
        )

        assert match is not None and match.id == record.id
        assert other_user_match is None
    finally:
        await connection.close()


@pytest.mark.asyncio
async def test_get_missing_record_raises_key_error(tmp_path: Path) -> None:
    connection = await connect(f"sqlite+aiosqlite:///{tmp_path / 'resume.db'}")
    try:
        await initialize_database(connection)
        repository = ResumeRepository(connection)

        with pytest.raises(KeyError):
            await repository.get(1)
    finally:
        await connection.close()


@pytest.mark.asyncio
async def test_pending_vector_indexes_and_health_check(tmp_path: Path) -> None:
    connection = await connect(f"sqlite+aiosqlite:///{tmp_path / 'resume.db'}")
    try:
        await initialize_database(connection)
        repository = ResumeRepository(connection)
        record = await repository.create(
            telegram_user_id=123,
            parsed_resume=parsed_resume(),
            original_filename="one.pdf",
            local_file_path="one.pdf",
        )

        pending = await repository.list_pending_vector_indexes()

        assert [item.id for item in pending] == [record.id]
        assert await repository.health_check()
    finally:
        await connection.close()
