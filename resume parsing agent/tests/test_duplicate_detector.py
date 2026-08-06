from pathlib import Path

import pytest

from resume_parser_agent.schemas import ContactInfo, ParsedResume
from resume_parser_agent.storage.database import connect
from resume_parser_agent.storage.migrations import initialize_database
from resume_parser_agent.storage.repositories import ResumeRepository
from resume_parser_agent.vectors.duplicate_detector import (
    DuplicateDecision,
    DuplicateDetector,
    DuplicateKind,
)
from resume_parser_agent.vectors.qdrant_store import VectorMatch


class FakeEmbeddingProvider:
    def __init__(self, vector: list[float] | None = None, should_fail: bool = False) -> None:
        self.vector = vector or [0.1, 0.2, 0.3]
        self.should_fail = should_fail

    def embed_text(self, text: str) -> list[float]:
        if self.should_fail:
            raise RuntimeError("embedding failed")
        return self.vector


class FakeVectorStore:
    def __init__(self, matches: list[VectorMatch] | None = None, should_fail: bool = False) -> None:
        self.matches = matches or []
        self.should_fail = should_fail
        self.upserted: list[tuple[int, int, list[float]]] = []

    async def search_similar(
        self,
        *,
        telegram_user_id: int,
        vector: list[float],
        limit: int,
        threshold: float,
    ) -> list[VectorMatch]:
        if self.should_fail:
            raise RuntimeError("qdrant down")
        return self.matches

    async def upsert_resume_vector(
        self,
        *,
        record_id: int,
        telegram_user_id: int,
        vector: list[float],
    ) -> None:
        if self.should_fail:
            raise RuntimeError("qdrant down")
        self.upserted.append((record_id, telegram_user_id, vector))


def parsed_resume(raw_text: str, name: str = "Jane Doe") -> ParsedResume:
    return ParsedResume(contact=ContactInfo(name=name), raw_text=raw_text)


async def make_repository(tmp_path: Path) -> tuple[ResumeRepository, object]:
    connection = await connect(f"sqlite+aiosqlite:///{tmp_path / 'resume.db'}")
    await initialize_database(connection)
    return ResumeRepository(connection), connection


@pytest.mark.asyncio
async def test_exact_duplicate_is_detected_for_same_user(tmp_path: Path) -> None:
    repository, connection = await make_repository(tmp_path)
    try:
        await repository.create(
            telegram_user_id=123,
            parsed_resume=parsed_resume("same"),
            original_filename="one.pdf",
            local_file_path="one.pdf",
        )
        detector = DuplicateDetector(
            repository=repository,
            embedding_provider=FakeEmbeddingProvider(),
            vector_store=FakeVectorStore(),
        )

        decision = await detector.find_duplicate(
            telegram_user_id=123,
            parsed_resume=parsed_resume("same"),
        )

        assert decision.kind == DuplicateKind.EXACT
        assert decision.should_ask_user
        assert decision.score == 1.0
    finally:
        await connection.close()


@pytest.mark.asyncio
async def test_near_duplicate_is_detected_with_vector_match(tmp_path: Path) -> None:
    repository, connection = await make_repository(tmp_path)
    try:
        detector = DuplicateDetector(
            repository=repository,
            embedding_provider=FakeEmbeddingProvider(),
            vector_store=FakeVectorStore(matches=[VectorMatch(record_id=42, score=0.91)]),
        )

        decision = await detector.find_duplicate(
            telegram_user_id=123,
            parsed_resume=parsed_resume("similar"),
        )

        assert decision.kind == DuplicateKind.NEAR
        assert decision.existing_record_id == 42
        assert decision.score == 0.91
    finally:
        await connection.close()


@pytest.mark.asyncio
async def test_same_user_scoping_ignores_other_user_exact_hash(tmp_path: Path) -> None:
    repository, connection = await make_repository(tmp_path)
    try:
        await repository.create(
            telegram_user_id=999,
            parsed_resume=parsed_resume("same"),
            original_filename="one.pdf",
            local_file_path="one.pdf",
        )
        detector = DuplicateDetector(
            repository=repository,
            embedding_provider=FakeEmbeddingProvider(),
            vector_store=FakeVectorStore(),
        )

        decision = await detector.find_duplicate(
            telegram_user_id=123,
            parsed_resume=parsed_resume("same"),
        )

        assert decision.kind == DuplicateKind.NONE
    finally:
        await connection.close()


@pytest.mark.asyncio
async def test_duplicate_detector_can_skip_vector_dedup_when_disabled(tmp_path: Path) -> None:
    repository, connection = await make_repository(tmp_path)
    try:
        detector = DuplicateDetector(
            repository=repository,
            embedding_provider=None,
            vector_store=None,
        )

        decision = await detector.find_duplicate(
            telegram_user_id=123,
            parsed_resume=parsed_resume("new resume"),
        )

        assert decision.kind == DuplicateKind.NONE
    finally:
        await connection.close()


@pytest.mark.asyncio
async def test_same_role_update_replaces_latest_and_file_path(tmp_path: Path) -> None:
    repository, connection = await make_repository(tmp_path)
    vector_store = FakeVectorStore()
    try:
        existing = await repository.create(
            telegram_user_id=123,
            parsed_resume=parsed_resume("old"),
            original_filename="old.pdf",
            local_file_path="old.pdf",
            target_role="Backend",
        )
        detector = DuplicateDetector(
            repository=repository,
            embedding_provider=FakeEmbeddingProvider(),
            vector_store=vector_store,
        )

        saved = await detector.save_with_duplicate_policy(
            telegram_user_id=123,
            parsed_resume=parsed_resume("new"),
            original_filename="new.pdf",
            local_file_path="new.pdf",
            target_role="Backend",
            decision=DuplicateDecision(kind=DuplicateKind.NEAR, existing_record_id=existing.id),
            user_confirmed_updated_resume=True,
            different_job_role=False,
        )

        assert saved.id == existing.id
        assert saved.version_number == 1
        assert saved.local_file_path == "new.pdf"
        assert saved.vector_indexing_status == "indexed"
        assert vector_store.upserted[0][0] == existing.id
    finally:
        await connection.close()


@pytest.mark.asyncio
async def test_different_role_creates_new_version_record(tmp_path: Path) -> None:
    repository, connection = await make_repository(tmp_path)
    try:
        existing = await repository.create(
            telegram_user_id=123,
            parsed_resume=parsed_resume("old"),
            original_filename="old.pdf",
            local_file_path="old.pdf",
            target_role="Backend",
        )
        detector = DuplicateDetector(
            repository=repository,
            embedding_provider=FakeEmbeddingProvider(),
            vector_store=FakeVectorStore(),
        )

        saved = await detector.save_with_duplicate_policy(
            telegram_user_id=123,
            parsed_resume=parsed_resume("new"),
            original_filename="new.pdf",
            local_file_path="new.pdf",
            target_role="Data",
            decision=DuplicateDecision(kind=DuplicateKind.NEAR, existing_record_id=existing.id),
            user_confirmed_updated_resume=True,
            different_job_role=True,
        )

        assert saved.id != existing.id
        assert saved.target_role == "Data"
        assert saved.version_number == 1
        assert saved.duplicate_status == "new_role_version"
    finally:
        await connection.close()


@pytest.mark.asyncio
async def test_qdrant_failure_keeps_sqlite_record_pending(tmp_path: Path) -> None:
    repository, connection = await make_repository(tmp_path)
    try:
        detector = DuplicateDetector(
            repository=repository,
            embedding_provider=FakeEmbeddingProvider(),
            vector_store=FakeVectorStore(should_fail=True),
        )

        saved = await detector.save_with_duplicate_policy(
            telegram_user_id=123,
            parsed_resume=parsed_resume("new"),
            original_filename="new.pdf",
            local_file_path="new.pdf",
            target_role=None,
            decision=DuplicateDecision(kind=DuplicateKind.NONE),
        )

        assert saved.id > 0
        assert saved.vector_indexing_status == "pending"
    finally:
        await connection.close()


@pytest.mark.asyncio
async def test_retry_pending_indexes_marks_records_indexed(tmp_path: Path) -> None:
    repository, connection = await make_repository(tmp_path)
    vector_store = FakeVectorStore()
    try:
        record = await repository.create(
            telegram_user_id=123,
            parsed_resume=parsed_resume("new"),
            original_filename="new.pdf",
            local_file_path="new.pdf",
        )
        detector = DuplicateDetector(
            repository=repository,
            embedding_provider=FakeEmbeddingProvider(),
            vector_store=vector_store,
        )

        attempted = await detector.retry_pending_indexes()
        updated = await repository.get(record.id)

        assert attempted == 1
        assert updated.vector_indexing_status == "indexed"
        assert vector_store.upserted[0][0] == record.id
    finally:
        await connection.close()
