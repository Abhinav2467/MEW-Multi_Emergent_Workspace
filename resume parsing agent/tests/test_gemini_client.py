from pathlib import Path
from types import SimpleNamespace

import pytest

from resume_parser_agent.errors import LLMCorrectionError, LLMCorrectionNoChangeError
from resume_parser_agent.llm.gemini_client import (
    GeminiCorrectionClient,
    apply_correction_to_record,
)
from resume_parser_agent.llm.prompts import build_correction_prompt
from resume_parser_agent.schemas import ContactInfo, CorrectionRequest, ParsedResume
from resume_parser_agent.storage.database import connect
from resume_parser_agent.storage.migrations import initialize_database
from resume_parser_agent.storage.repositories import ResumeRepository


class FakeModels:
    def __init__(self, response_text: str | None = None, should_fail: bool = False) -> None:
        self.response_text = response_text
        self.should_fail = should_fail
        self.calls: list[dict[str, object]] = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if self.should_fail:
            raise RuntimeError("gemini down")
        return SimpleNamespace(text=self.response_text)


class FakeGenaiClient:
    def __init__(self, models: FakeModels) -> None:
        self.models = models


def parsed_resume(name: str = "Jane Doe", email: str = "jane@example.com") -> ParsedResume:
    return ParsedResume(contact=ContactInfo(name=name, email=email), raw_text=name)


def test_build_correction_prompt_includes_current_json_and_feedback() -> None:
    prompt = build_correction_prompt(
        CorrectionRequest(
            resume_id="1",
            correction_text="Email is jane@new.com",
            current_resume=parsed_resume(),
        )
    )

    assert "jane@example.com" in prompt
    assert "Email is jane@new.com" in prompt
    assert "raw_text" in prompt
    assert "return the current JSON unchanged" in prompt


@pytest.mark.asyncio
async def test_valid_correction_returns_validated_resume() -> None:
    corrected = parsed_resume(email="jane@new.com").model_dump_json()
    models = FakeModels(response_text=corrected)
    client = GeminiCorrectionClient(api_key=None, client=FakeGenaiClient(models))

    result = await client.apply_user_correction(
        CorrectionRequest(
            resume_id="1",
            correction_text="Email is jane@new.com",
            current_resume=parsed_resume(),
        )
    )

    assert result.contact.email == "jane@new.com"
    assert models.calls[0]["model"] == "gemini-2.5-flash"
    assert models.calls[0]["config"]["response_mime_type"] == "application/json"


@pytest.mark.asyncio
async def test_malformed_gemini_response_is_rejected_safely() -> None:
    client = GeminiCorrectionClient(
        api_key=None,
        client=FakeGenaiClient(FakeModels(response_text="{not json")),
    )

    with pytest.raises(LLMCorrectionError):
        await client.apply_user_correction(
            CorrectionRequest(
                resume_id="1",
                correction_text="Fix email",
                current_resume=parsed_resume(),
            )
        )


@pytest.mark.asyncio
async def test_gemini_outage_raises_correction_error_without_losing_record(tmp_path: Path) -> None:
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
        client = GeminiCorrectionClient(
            api_key=None,
            client=FakeGenaiClient(FakeModels(should_fail=True)),
        )

        with pytest.raises(LLMCorrectionError):
            await apply_correction_to_record(
                repository=repository,
                record_id=record.id,
                correction_text="Fix email",
                client=client,
            )

        unchanged = await repository.get(record.id)
        assert unchanged.parsed_json["contact"]["email"] == "jane@example.com"
    finally:
        await connection.close()


@pytest.mark.asyncio
async def test_apply_correction_to_record_saves_back_to_sqlite(tmp_path: Path) -> None:
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
        client = GeminiCorrectionClient(
            api_key=None,
            client=FakeGenaiClient(FakeModels(response_text=parsed_resume(email="jane@new.com").model_dump_json())),
        )

        corrected = await apply_correction_to_record(
            repository=repository,
            record_id=record.id,
            correction_text="Email is jane@new.com",
            client=client,
        )
        saved = await repository.get(record.id)

        assert corrected.contact.email == "jane@new.com"
        assert saved.parsed_json["contact"]["email"] == "jane@new.com"
        assert saved.duplicate_status == "corrected"
        assert saved.vector_indexing_status == "pending"
    finally:
        await connection.close()


@pytest.mark.asyncio
async def test_apply_correction_to_record_rejects_unchanged_ai_result(tmp_path: Path) -> None:
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
        client = GeminiCorrectionClient(
            api_key=None,
            client=FakeGenaiClient(FakeModels(response_text=parsed_resume().model_dump_json())),
        )

        with pytest.raises(LLMCorrectionNoChangeError):
            await apply_correction_to_record(
                repository=repository,
                record_id=record.id,
                correction_text="The name is wrong",
                client=client,
            )

        saved = await repository.get(record.id)
        assert saved.duplicate_status == "new"
        assert saved.parsed_json["contact"]["name"] == "Jane Doe"
    finally:
        await connection.close()
