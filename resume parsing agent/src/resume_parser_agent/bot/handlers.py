"""Telegram handlers for resume uploads and correction flow."""

from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from resume_parser_agent.bot.formatters import (
    format_error_message,
    format_json_block,
    format_summary,
)
from resume_parser_agent.bot.corrections import apply_local_correction
from resume_parser_agent.bot.corrections import correction_prompt_for
from resume_parser_agent.bot.session_store import SessionState, SessionStore, UserParseSession
from resume_parser_agent.dashboard.events import DashboardEventBus
from resume_parser_agent.llm.gemini_client import GeminiCorrectionClient, apply_correction_to_record
from resume_parser_agent.errors import (
    LLMCorrectionNoChangeError,
    ResumeParserError,
    UnauthorizedUserError,
)
from resume_parser_agent.logging_config import get_logger
from resume_parser_agent.parser.service import ResumeParserService
from resume_parser_agent.storage.repositories import ResumeRepository
from resume_parser_agent.storage.resume_files import store_resume_file
from resume_parser_agent.vectors.duplicate_detector import DuplicateDetector, DuplicateKind


logger = get_logger(__name__)
PARSING_MESSAGE = "Parsing your resume. Please wait until I finish."
BUSY_MESSAGE = "I'm still parsing your previous resume. Please wait until I finish."


@dataclass(slots=True)
class BotDependencies:
    """Runtime dependencies used by Telegram handlers."""

    parser_service: ResumeParserService
    session_store: SessionStore
    storage_dir: Path
    allowed_chat_ids: tuple[int, ...]
    repository: ResumeRepository | None = None
    duplicate_detector: DuplicateDetector | None = None
    event_bus: DashboardEventBus | None = None
    correction_client: GeminiCorrectionClient | None = None


async def handle_start(update: Any, context: Any) -> None:
    """Reply to /start with a concise upload prompt."""

    if not _is_authorized(update, _deps(context).allowed_chat_ids):
        await _reply(update, UnauthorizedUserError().user_message)
        return
    await _reply(update, "Send me a PDF or DOCX resume and I will parse it.")


async def handle_resume_upload(update: Any, context: Any) -> None:
    """Download, parse, store, and summarize an uploaded resume document."""

    deps = _deps(context)
    chat_id = _chat_id(update)
    if not _is_authorized(update, deps.allowed_chat_ids):
        await _reply(update, UnauthorizedUserError().user_message)
        return

    document = getattr(getattr(update, "message", None), "document", None)
    if document is None:
        await _reply(update, "Please upload a PDF or DOCX resume file.")
        return

    session = await deps.session_store.get(chat_id)
    if session.state == SessionState.PROCESSING:
        await _reply(update, BUSY_MESSAGE)
        return

    session.state = SessionState.PROCESSING
    session.parsed_resume = None
    session.stored_resume_path = None
    session.original_filename = None
    session.record_id = None
    session.duplicate_decision = None
    session.correction_text = None
    await deps.session_store.set(session)
    await _reply(update, PARSING_MESSAGE)

    try:
        with TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / Path(document.file_name or "resume").name
            telegram_file = await document.get_file()
            await telegram_file.download_to_drive(custom_path=source_path)

            parsed = deps.parser_service.parse_file(source_path)
            stored = store_resume_file(
                source_path,
                person_name=parsed.contact.name,
                storage_dir=deps.storage_dir,
            )

        record_id: int | None = None
        if deps.repository is not None:
            record = await deps.repository.create(
                telegram_user_id=chat_id,
                parsed_resume=parsed,
                original_filename=stored.original_filename,
                local_file_path=stored.relative_path,
            )
            record_id = record.id

        session = UserParseSession(
            chat_id=chat_id,
            state=SessionState.IDLE,
            parsed_resume=parsed,
            stored_resume_path=stored.relative_path,
            original_filename=stored.original_filename,
            record_id=record_id,
            duplicate_decision=None,
        )
        await deps.session_store.set(session)
        
        import json
        skills_json = json.dumps({"skills": parsed.skills}, indent=2)
        await _reply(
            update,
            f"```json\n{skills_json}\n```",
        )
    except Exception as exc:
        logger.exception("Resume upload handling failed", extra={"chat_id": chat_id})
        session.state = SessionState.IDLE
        await deps.session_store.set(session)
        await _reply(update, format_error_message(exc))


async def handle_confirmation(update: Any, context: Any) -> None:
    """Handle yes/no confirmation after parsing."""

    deps = _deps(context)
    chat_id = _chat_id(update)
    if not _is_authorized(update, deps.allowed_chat_ids):
        await _reply(update, UnauthorizedUserError().user_message)
        return

    session = await deps.session_store.get(chat_id)
    if session.state == SessionState.PROCESSING:
        await _reply(update, BUSY_MESSAGE)
        return

    text = _message_text(update).lower()
    if session.state != SessionState.AWAITING_CONFIRMATION:
        if session.state == SessionState.AWAITING_CORRECTION:
            await handle_correction_message(update, context)
        else:
            await _reply(update, "Please upload a resume first.")
        return

    if session.duplicate_decision is not None and session.duplicate_decision.should_ask_user:
        if text in {"no", "n", "keep existing", "not updated"}:
            session.state = SessionState.IDLE
            await deps.session_store.set(session)
            await _reply(update, "Okay, I left the existing saved resume unchanged.")
            return

        if text not in {"same role", "different role", "yes", "y", "updated"}:
            await _reply(
                update,
                "Please reply `same role`, `different role`, or `no` for the similar saved resume.",
            )
            return

        if deps.duplicate_detector is not None and session.parsed_resume is not None:
            record = await deps.duplicate_detector.save_with_duplicate_policy(
                telegram_user_id=chat_id,
                parsed_resume=session.parsed_resume,
                original_filename=session.original_filename or "resume",
                local_file_path=session.stored_resume_path or "",
                target_role=None,
                decision=session.duplicate_decision,
                user_confirmed_updated_resume=True,
                different_job_role=text == "different role",
            )
            session.record_id = record.id
            if deps.event_bus is not None:
                await deps.event_bus.publish_resume_saved(record.id)
            session.state = SessionState.IDLE
            await deps.session_store.set(session)
            await _reply(update, "Great, I saved the updated resume decision.")
            return

    if text in {"yes", "y", "correct", "looks good"}:
        session.state = SessionState.IDLE
        await deps.session_store.set(session)
        await _reply(update, "Great, I saved the parsed resume.")
        return

    session.state = SessionState.AWAITING_CORRECTION
    await deps.session_store.set(session)
    if text not in {"no", "n"}:
        await handle_correction_message(update, context)
        return
    await _reply(update, "Tell me what is wrong or paste the corrected details.")


async def handle_correction_message(update: Any, context: Any) -> None:
    """Collect correction text for the later Gemini correction step."""

    deps = _deps(context)
    chat_id = _chat_id(update)
    if not _is_authorized(update, deps.allowed_chat_ids):
        await _reply(update, UnauthorizedUserError().user_message)
        return

    session = await deps.session_store.get(chat_id)
    if session.state == SessionState.PROCESSING:
        await _reply(update, BUSY_MESSAGE)
        return

    if session.state != SessionState.AWAITING_CORRECTION:
        await _reply(update, "Please upload a resume first.")
        return

    session.correction_text = _message_text(update)
    if (
        deps.repository is not None
        and deps.correction_client is not None
        and session.record_id is not None
    ):
        try:
            corrected = await apply_correction_to_record(
                repository=deps.repository,
                record_id=session.record_id,
                correction_text=session.correction_text,
                client=deps.correction_client,
            )
            if deps.event_bus is not None:
                await deps.event_bus.publish_resume_saved(session.record_id)
            session.parsed_resume = corrected
            session.state = SessionState.IDLE
            await deps.session_store.set(session)
            await _reply(
                update,
                "\n\n".join(
                    [
                        "Thanks, I applied the AI correction and updated the saved JSON.",
                        format_summary(corrected),
                    ]
                ),
            )
            return
        except LLMCorrectionNoChangeError:
            session.state = SessionState.AWAITING_CORRECTION
            await deps.session_store.set(session)
            await _reply(update, correction_prompt_for(session.correction_text))
            return
        except Exception as exc:
            logger.exception("Resume correction handling failed", extra={"chat_id": chat_id})
            await _reply(update, format_error_message(exc))
            return

    if session.parsed_resume is not None:
        corrected = apply_local_correction(session.parsed_resume, session.correction_text)
        if corrected is not None:
            session.parsed_resume = corrected
            if deps.repository is not None and session.record_id is not None:
                await deps.repository.replace_latest_version(
                    record_id=session.record_id,
                    parsed_resume=corrected,
                    original_filename=session.original_filename or "resume",
                    local_file_path=session.stored_resume_path or "",
                    duplicate_status="corrected",
                    vector_indexing_status="pending",
                )
                if deps.event_bus is not None:
                    await deps.event_bus.publish_resume_saved(session.record_id)
            session.state = SessionState.IDLE
            await deps.session_store.set(session)
            await _reply(
                update,
                "\n\n".join(
                    [
                        "Updated parsed details.",
                        format_summary(corrected),
                        "Full JSON is saved in the dashboard.",
                    ]
                ),
            )
            return

    session.state = SessionState.AWAITING_CORRECTION
    await deps.session_store.set(session)
    await _reply(update, correction_prompt_for(session.correction_text))


async def handle_error(update: object, context: Any) -> None:
    """Log and surface unexpected handler errors gracefully."""

    error = getattr(context, "error", None)
    message = format_error_message(error if isinstance(error, Exception) else ResumeParserError())
    if update is not None:
        await _reply(update, message)


def _deps(context: Any) -> BotDependencies:
    return context.application.bot_data["dependencies"]


def _chat_id(update: Any) -> int:
    return int(update.effective_chat.id)


def _is_authorized(update: Any, allowed_chat_ids: tuple[int, ...]) -> bool:
    return not allowed_chat_ids or _chat_id(update) in allowed_chat_ids


def _message_text(update: Any) -> str:
    return str(getattr(getattr(update, "message", None), "text", "")).strip()


async def _reply(update: Any, text: str) -> None:
    await update.effective_message.reply_text(text)
