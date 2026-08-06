"""Duplicate detection and duplicate-aware persistence."""

from dataclasses import dataclass
from enum import StrEnum

from resume_parser_agent.schemas import ParsedResume
from resume_parser_agent.storage.models import ResumeRecord
from resume_parser_agent.storage.repositories import ResumeRepository, create_text_hash
from resume_parser_agent.vectors.embeddings import EmbeddingProvider
from resume_parser_agent.vectors.qdrant_store import VectorStore


class DuplicateKind(StrEnum):
    """Duplicate detection result kind."""

    NONE = "none"
    EXACT = "exact"
    NEAR = "near"


@dataclass(frozen=True, slots=True)
class DuplicateDecision:
    """Duplicate detector decision."""

    kind: DuplicateKind
    existing_record_id: int | None = None
    score: float | None = None
    vector_error: str | None = None

    @property
    def should_ask_user(self) -> bool:
        return self.kind in {DuplicateKind.EXACT, DuplicateKind.NEAR}


class DuplicateDetector:
    """Same-user exact and near-duplicate detector."""

    def __init__(
        self,
        *,
        repository: ResumeRepository,
        embedding_provider: EmbeddingProvider | None,
        vector_store: VectorStore | None,
        similarity_threshold: float = 0.88,
    ) -> None:
        self.repository = repository
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store
        self.similarity_threshold = similarity_threshold

    async def find_duplicate(
        self,
        *,
        telegram_user_id: int,
        parsed_resume: ParsedResume,
    ) -> DuplicateDecision:
        """Find exact hash or near-vector duplicates for the same Telegram user."""

        text = parsed_resume.raw_text or ""
        exact = await self.repository.find_by_text_hash(
            telegram_user_id=telegram_user_id,
            text_hash=create_text_hash(text),
        )
        if exact is not None:
            return DuplicateDecision(
                kind=DuplicateKind.EXACT,
                existing_record_id=exact.id,
                score=1.0,
            )

        if self.embedding_provider is None or self.vector_store is None:
            return DuplicateDecision(kind=DuplicateKind.NONE)

        try:
            vector = self.embedding_provider.embed_text(text)
            matches = await self.vector_store.search_similar(
                telegram_user_id=telegram_user_id,
                vector=vector,
                limit=1,
                threshold=self.similarity_threshold,
            )
        except Exception as exc:
            return DuplicateDecision(kind=DuplicateKind.NONE, vector_error=str(exc))

        if matches:
            best = matches[0]
            return DuplicateDecision(
                kind=DuplicateKind.NEAR,
                existing_record_id=best.record_id,
                score=best.score,
            )
        return DuplicateDecision(kind=DuplicateKind.NONE)

    async def save_with_duplicate_policy(
        self,
        *,
        telegram_user_id: int,
        parsed_resume: ParsedResume,
        original_filename: str,
        local_file_path: str,
        target_role: str | None,
        decision: DuplicateDecision,
        user_confirmed_updated_resume: bool = False,
        different_job_role: bool = False,
    ) -> ResumeRecord:
        """Persist a resume using the duplicate/update policy."""

        person_name = parsed_resume.contact.name or "Unknown"
        if decision.should_ask_user and user_confirmed_updated_resume and not different_job_role:
            latest = await self.repository.latest_for_person_role(
                telegram_user_id=telegram_user_id,
                person_name=person_name,
                target_role=target_role,
            )
            record_id = latest.id if latest else decision.existing_record_id
            if record_id is not None:
                record = await self.repository.replace_latest_version(
                    record_id=record_id,
                    parsed_resume=parsed_resume,
                    original_filename=original_filename,
                    local_file_path=local_file_path,
                    duplicate_status="updated",
                )
            else:
                record = await self.repository.create(
                    telegram_user_id=telegram_user_id,
                    parsed_resume=parsed_resume,
                    original_filename=original_filename,
                    local_file_path=local_file_path,
                    target_role=target_role,
                    duplicate_status="updated",
                )
        else:
            duplicate_status = "new"
            if decision.should_ask_user and different_job_role:
                duplicate_status = "new_role_version"
            elif decision.should_ask_user:
                duplicate_status = decision.kind.value
            record = await self.repository.create(
                telegram_user_id=telegram_user_id,
                parsed_resume=parsed_resume,
                original_filename=original_filename,
                local_file_path=local_file_path,
                target_role=target_role,
                duplicate_status=duplicate_status,
            )

        await self.index_record(telegram_user_id=telegram_user_id, record=record)
        return await self.repository.get(record.id)

    async def index_record(self, *, telegram_user_id: int, record: ResumeRecord) -> None:
        """Best-effort vector indexing; SQLite remains source of truth."""

        try:
            if self.embedding_provider is None or self.vector_store is None:
                await self.repository.update_vector_indexing_status(record.id, "skipped")
                return
            vector = self.embedding_provider.embed_text(str(record.parsed_json.get("raw_text") or ""))
            await self.vector_store.upsert_resume_vector(
                record_id=record.id,
                telegram_user_id=telegram_user_id,
                vector=vector,
            )
        except Exception:
            await self.repository.update_vector_indexing_status(record.id, "pending")
            return
        await self.repository.update_vector_indexing_status(record.id, "indexed")

    async def retry_pending_indexes(self, *, limit: int = 50) -> int:
        """Retry pending vector indexing records and return how many were attempted."""

        pending = await self.repository.list_pending_vector_indexes(limit=limit)
        for record in pending:
            await self.index_record(telegram_user_id=record.telegram_user_id, record=record)
        return len(pending)
