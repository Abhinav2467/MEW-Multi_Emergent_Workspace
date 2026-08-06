from pathlib import Path
from types import SimpleNamespace

import pytest

from resume_parser_agent.bot.handlers import (
    BotDependencies,
    handle_confirmation,
    handle_correction_message,
    handle_resume_upload,
    handle_start,
)
from resume_parser_agent.bot.session_store import SessionState, SessionStore
from resume_parser_agent.errors import UnsupportedFileTypeError
from resume_parser_agent.parser.service import ResumeParserService
from resume_parser_agent.storage.database import connect
from resume_parser_agent.storage.migrations import initialize_database
from resume_parser_agent.storage.repositories import ResumeRepository
from resume_parser_agent.vectors.duplicate_detector import DuplicateDetector
from tests.test_duplicate_detector import FakeEmbeddingProvider, FakeVectorStore
from tests.test_parser_service import make_docx


class FakeMessage:
    def __init__(self, *, text: str = "", document: object | None = None) -> None:
        self.text = text
        self.document = document
        self.replies: list[str] = []

    async def reply_text(self, text: str) -> None:
        self.replies.append(text)


class FakeTelegramFile:
    def __init__(self, source: Path) -> None:
        self.source = source

    async def download_to_drive(self, custom_path: Path) -> None:
        custom_path.write_bytes(self.source.read_bytes())


class FakeDocument:
    def __init__(self, source: Path) -> None:
        self.source = source
        self.file_name = source.name

    async def get_file(self) -> FakeTelegramFile:
        return FakeTelegramFile(self.source)


class FailingParserService:
    def parse_file(self, file_path: Path):
        raise UnsupportedFileTypeError(file_path.suffix)


class FakeCorrectionClient:
    def __init__(self, corrected):
        self.corrected = corrected
        self.requests = []

    async def apply_user_correction(self, request):
        self.requests.append(request)
        return self.corrected


def make_update(chat_id: int, message: FakeMessage) -> SimpleNamespace:
    return SimpleNamespace(
        effective_chat=SimpleNamespace(id=chat_id),
        effective_message=message,
        message=message,
    )


def make_context(deps: BotDependencies) -> SimpleNamespace:
    return SimpleNamespace(application=SimpleNamespace(bot_data={"dependencies": deps}))


def make_deps(tmp_path: Path, allowed_chat_ids: tuple[int, ...] = (123,)) -> BotDependencies:
    return BotDependencies(
        parser_service=ResumeParserService(),
        session_store=SessionStore(),
        storage_dir=tmp_path / "stored",
        allowed_chat_ids=allowed_chat_ids,
    )


@pytest.mark.asyncio
async def test_unauthorized_user_is_rejected(tmp_path: Path) -> None:
    deps = make_deps(tmp_path, allowed_chat_ids=(123,))
    message = FakeMessage()

    await handle_start(make_update(999, message), make_context(deps))

    assert message.replies == ["You are not authorized to use this bot."]


@pytest.mark.asyncio
async def test_resume_upload_parses_stores_and_asks_for_confirmation(tmp_path: Path) -> None:
    source = make_docx(tmp_path / "resume.docx")
    deps = make_deps(tmp_path)
    message = FakeMessage(document=FakeDocument(source))

    await handle_resume_upload(make_update(123, message), make_context(deps))

    assert message.replies[0] == "Parsing your resume. Please wait until I finish."
    assert "Parsing Complete!" in message.replies[1]
    assert "Full JSON is saved in the dashboard." in message.replies[1]
    assert "```json" not in message.replies[1]
    assert "Are these details correct?" in message.replies[1]
    stored_files = list((tmp_path / "stored").glob("Jane_Doe__*.docx"))
    assert len(stored_files) == 1
    session = await deps.session_store.get(123)
    assert session.state == SessionState.AWAITING_CONFIRMATION
    assert session.stored_resume_path == stored_files[0].name


@pytest.mark.asyncio
async def test_parser_error_becomes_friendly_message(tmp_path: Path) -> None:
    source = tmp_path / "resume.txt"
    source.write_text("not supported", encoding="utf-8")
    deps = make_deps(tmp_path)
    message = FakeMessage(document=FakeDocument(source))

    await handle_resume_upload(make_update(123, message), make_context(deps))

    assert message.replies == [
        "Parsing your resume. Please wait until I finish.",
        "Please upload a PDF or DOCX resume.",
    ]
    assert (await deps.session_store.get(123)).state == SessionState.IDLE


@pytest.mark.asyncio
async def test_upload_is_rejected_while_previous_parse_is_processing(tmp_path: Path) -> None:
    source = make_docx(tmp_path / "resume.docx")
    deps = make_deps(tmp_path)
    session = await deps.session_store.get(123)
    session.state = SessionState.PROCESSING
    await deps.session_store.set(session)
    message = FakeMessage(document=FakeDocument(source))

    await handle_resume_upload(make_update(123, message), make_context(deps))

    assert message.replies == [
        "I'm still parsing your previous resume. Please wait until I finish."
    ]
    assert not (tmp_path / "stored").exists()


@pytest.mark.asyncio
async def test_text_is_rejected_while_parse_is_processing(tmp_path: Path) -> None:
    deps = make_deps(tmp_path)
    session = await deps.session_store.get(123)
    session.state = SessionState.PROCESSING
    await deps.session_store.set(session)
    message = FakeMessage(text="No")

    await handle_confirmation(make_update(123, message), make_context(deps))

    assert message.replies == [
        "I'm still parsing your previous resume. Please wait until I finish."
    ]


@pytest.mark.asyncio
async def test_parser_exception_resets_processing_state(tmp_path: Path) -> None:
    source = make_docx(tmp_path / "resume.docx")
    deps = make_deps(tmp_path)
    deps.parser_service = FailingParserService()  # type: ignore[assignment]
    message = FakeMessage(document=FakeDocument(source))

    await handle_resume_upload(make_update(123, message), make_context(deps))

    assert message.replies == [
        "Parsing your resume. Please wait until I finish.",
        "Please upload a PDF or DOCX resume.",
    ]
    assert (await deps.session_store.get(123)).state == SessionState.IDLE


@pytest.mark.asyncio
async def test_confirmation_yes_saves_resume_state(tmp_path: Path) -> None:
    deps = make_deps(tmp_path)
    session = await deps.session_store.get(123)
    session.state = SessionState.AWAITING_CONFIRMATION
    await deps.session_store.set(session)
    message = FakeMessage(text="yes")

    await handle_confirmation(make_update(123, message), make_context(deps))

    assert message.replies == ["Great, I saved the parsed resume."]
    assert (await deps.session_store.get(123)).state == SessionState.IDLE


@pytest.mark.asyncio
async def test_confirmation_no_enters_correction_state(tmp_path: Path) -> None:
    deps = make_deps(tmp_path)
    session = await deps.session_store.get(123)
    session.state = SessionState.AWAITING_CONFIRMATION
    await deps.session_store.set(session)
    message = FakeMessage(text="no")

    await handle_confirmation(make_update(123, message), make_context(deps))

    assert message.replies == ["Tell me what is wrong or paste the corrected details."]
    assert (await deps.session_store.get(123)).state == SessionState.AWAITING_CORRECTION


@pytest.mark.asyncio
async def test_vague_confirmation_feedback_gets_targeted_prompt(tmp_path: Path) -> None:
    deps = make_deps(tmp_path)
    session = await deps.session_store.get(123)
    session.state = SessionState.AWAITING_CONFIRMATION
    session.parsed_resume = ResumeParserService().parse_file(make_docx(tmp_path / "resume.docx"))
    await deps.session_store.set(session)
    message = FakeMessage(text="My name is wrong and my phone no is incorrect")

    await handle_confirmation(make_update(123, message), make_context(deps))

    assert message.replies == [
        "Please send the corrected name and phone like `My name is Jane Doe` and `Phone: +91 98765 43210`."
    ]
    stored = await deps.session_store.get(123)
    assert stored.state == SessionState.AWAITING_CORRECTION
    assert stored.correction_text == "My name is wrong and my phone no is incorrect"


@pytest.mark.asyncio
async def test_concrete_confirmation_feedback_applies_without_repeat(tmp_path: Path) -> None:
    deps = make_deps(tmp_path)
    session = await deps.session_store.get(123)
    session.state = SessionState.AWAITING_CONFIRMATION
    session.parsed_resume = ResumeParserService().parse_file(make_docx(tmp_path / "resume.docx"))
    await deps.session_store.set(session)
    message = FakeMessage(text="My name is Regandla Sai Yasvitha")

    await handle_confirmation(make_update(123, message), make_context(deps))

    assert "Updated parsed details." in message.replies[0]
    assert "Name: Regandla Sai Yasvitha" in message.replies[0]
    assert (await deps.session_store.get(123)).state == SessionState.IDLE


@pytest.mark.asyncio
async def test_correction_message_is_collected(tmp_path: Path) -> None:
    deps = make_deps(tmp_path)
    session = await deps.session_store.get(123)
    session.state = SessionState.AWAITING_CORRECTION
    await deps.session_store.set(session)
    message = FakeMessage(text="The phone number is wrong.")

    await handle_correction_message(make_update(123, message), make_context(deps))

    stored = await deps.session_store.get(123)
    assert message.replies == [
        "Please send the corrected phone like `Phone: +91 98765 43210`."
    ]
    assert stored.state == SessionState.AWAITING_CORRECTION
    assert stored.correction_text == "The phone number is wrong."


@pytest.mark.asyncio
async def test_local_name_correction_updates_session_and_record(tmp_path: Path) -> None:
    connection = await connect(f"sqlite+aiosqlite:///{tmp_path / 'resume.db'}")
    try:
        await initialize_database(connection)
        repository = ResumeRepository(connection)
        parsed = ResumeParserService().parse_file(make_docx(tmp_path / "resume.docx"))
        record = await repository.create(
            telegram_user_id=123,
            parsed_resume=parsed,
            original_filename="resume.docx",
            local_file_path="resume.docx",
        )
        deps = make_deps(tmp_path)
        deps.repository = repository
        session = await deps.session_store.get(123)
        session.state = SessionState.AWAITING_CORRECTION
        session.parsed_resume = parsed
        session.record_id = record.id
        session.original_filename = "resume.docx"
        session.stored_resume_path = "resume.docx"
        await deps.session_store.set(session)
        message = FakeMessage(text="My name is Regandla Sai Yasvitha")

        await handle_correction_message(make_update(123, message), make_context(deps))

        saved = await repository.get(record.id)
        updated_session = await deps.session_store.get(123)
        assert "Updated parsed details." in message.replies[0]
        assert "Name: Regandla Sai Yasvitha" in message.replies[0]
        assert saved.parsed_json["contact"]["name"] == "Regandla Sai Yasvitha"
        assert updated_session.state == SessionState.IDLE
    finally:
        await connection.close()


@pytest.mark.asyncio
async def test_ai_correction_applies_when_configured(tmp_path: Path) -> None:
    connection = await connect(f"sqlite+aiosqlite:///{tmp_path / 'resume.db'}")
    try:
        await initialize_database(connection)
        repository = ResumeRepository(connection)
        parsed = ResumeParserService().parse_file(make_docx(tmp_path / "resume.docx"))
        record = await repository.create(
            telegram_user_id=123,
            parsed_resume=parsed,
            original_filename="resume.docx",
            local_file_path="resume.docx",
        )
        corrected = parsed.model_copy(deep=True)
        corrected.contact.name = "Jahnavi Modi"
        correction_client = FakeCorrectionClient(corrected)
        deps = make_deps(tmp_path)
        deps.repository = repository
        deps.correction_client = correction_client  # type: ignore[assignment]
        session = await deps.session_store.get(123)
        session.state = SessionState.AWAITING_CORRECTION
        session.parsed_resume = parsed
        session.record_id = record.id
        session.original_filename = "resume.docx"
        session.stored_resume_path = "resume.docx"
        await deps.session_store.set(session)
        message = FakeMessage(text="The name is wrong")

        await handle_correction_message(make_update(123, message), make_context(deps))

        saved = await repository.get(record.id)
        assert "Thanks, I applied the AI correction" in message.replies[0]
        assert "Name: Jahnavi Modi" in message.replies[0]
        assert saved.parsed_json["contact"]["name"] == "Jahnavi Modi"
        assert correction_client.requests[0].correction_text == "The name is wrong"
        assert (await deps.session_store.get(123)).state == SessionState.IDLE
    finally:
        await connection.close()


@pytest.mark.asyncio
async def test_ai_correction_no_change_asks_for_corrected_value(tmp_path: Path) -> None:
    connection = await connect(f"sqlite+aiosqlite:///{tmp_path / 'resume.db'}")
    try:
        await initialize_database(connection)
        repository = ResumeRepository(connection)
        parsed = ResumeParserService().parse_file(make_docx(tmp_path / "resume.docx"))
        record = await repository.create(
            telegram_user_id=123,
            parsed_resume=parsed,
            original_filename="resume.docx",
            local_file_path="resume.docx",
        )
        deps = make_deps(tmp_path)
        deps.repository = repository
        deps.correction_client = FakeCorrectionClient(parsed)  # type: ignore[assignment]
        session = await deps.session_store.get(123)
        session.state = SessionState.AWAITING_CORRECTION
        session.parsed_resume = parsed
        session.record_id = record.id
        session.original_filename = "resume.docx"
        session.stored_resume_path = "resume.docx"
        await deps.session_store.set(session)
        message = FakeMessage(text="The name is wrong")

        await handle_correction_message(make_update(123, message), make_context(deps))

        saved = await repository.get(record.id)
        assert message.replies == [
            "Please send the corrected name like `My name is Jane Doe`."
        ]
        assert saved.duplicate_status == "new"
        assert (await deps.session_store.get(123)).state == SessionState.AWAITING_CORRECTION
    finally:
        await connection.close()


@pytest.mark.asyncio
async def test_resume_upload_persists_record_and_stores_session_id(tmp_path: Path) -> None:
    connection = await connect(f"sqlite+aiosqlite:///{tmp_path / 'resume.db'}")
    try:
        await initialize_database(connection)
        repository = ResumeRepository(connection)
        deps = make_deps(tmp_path)
        deps.repository = repository
        source = make_docx(tmp_path / "resume.docx")
        message = FakeMessage(document=FakeDocument(source))

        await handle_resume_upload(make_update(123, message), make_context(deps))

        records = await repository.list_for_user(123)
        session = await deps.session_store.get(123)
        assert len(records) == 1
        assert records[0].person_name == "Jane Doe"
        assert session.record_id == records[0].id
    finally:
        await connection.close()


@pytest.mark.asyncio
async def test_duplicate_upload_prompts_before_creating_new_record(tmp_path: Path) -> None:
    connection = await connect(f"sqlite+aiosqlite:///{tmp_path / 'resume.db'}")
    try:
        await initialize_database(connection)
        repository = ResumeRepository(connection)
        existing = ResumeParserService().parse_file(make_docx(tmp_path / "existing.docx"))
        await repository.create(
            telegram_user_id=123,
            parsed_resume=existing,
            original_filename="existing.docx",
            local_file_path="existing.docx",
        )
        deps = make_deps(tmp_path)
        deps.repository = repository
        deps.duplicate_detector = DuplicateDetector(
            repository=repository,
            embedding_provider=FakeEmbeddingProvider(),
            vector_store=FakeVectorStore(),
        )
        message = FakeMessage(document=FakeDocument(make_docx(tmp_path / "duplicate.docx")))

        await handle_resume_upload(make_update(123, message), make_context(deps))

        records = await repository.list_for_user(123)
        session = await deps.session_store.get(123)
        assert len(records) == 1
        assert session.duplicate_decision is not None
        assert "I found a similar resume already saved" in message.replies[1]
    finally:
        await connection.close()


@pytest.mark.asyncio
async def test_duplicate_same_role_confirmation_replaces_without_correction_prompt(tmp_path: Path) -> None:
    connection = await connect(f"sqlite+aiosqlite:///{tmp_path / 'resume.db'}")
    try:
        await initialize_database(connection)
        repository = ResumeRepository(connection)
        existing = ResumeParserService().parse_file(make_docx(tmp_path / "existing.docx"))
        record = await repository.create(
            telegram_user_id=123,
            parsed_resume=existing,
            original_filename="existing.docx",
            local_file_path="existing.docx",
        )
        deps = make_deps(tmp_path)
        deps.repository = repository
        deps.duplicate_detector = DuplicateDetector(
            repository=repository,
            embedding_provider=FakeEmbeddingProvider(),
            vector_store=FakeVectorStore(),
        )
        upload_message = FakeMessage(document=FakeDocument(make_docx(tmp_path / "duplicate.docx")))
        await handle_resume_upload(make_update(123, upload_message), make_context(deps))

        confirm_message = FakeMessage(text="same role")
        await handle_confirmation(make_update(123, confirm_message), make_context(deps))

        records = await repository.list_for_user(123)
        session = await deps.session_store.get(123)
        assert len(records) == 1
        assert records[0].id == record.id
        assert records[0].duplicate_status == "updated"
        assert session.state == SessionState.IDLE
        assert confirm_message.replies == ["Great, I saved the updated resume decision."]
    finally:
        await connection.close()
