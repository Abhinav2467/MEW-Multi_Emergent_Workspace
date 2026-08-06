"""In-memory Telegram user session state."""

from dataclasses import dataclass
from enum import StrEnum
from asyncio import Lock

from resume_parser_agent.schemas import ParsedResume
from resume_parser_agent.vectors.duplicate_detector import DuplicateDecision


class SessionState(StrEnum):
    """Supported Telegram conversation states."""

    IDLE = "idle"
    PROCESSING = "processing"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    AWAITING_CORRECTION = "awaiting_correction"


@dataclass(slots=True)
class UserParseSession:
    """Temporary state for one Telegram user's latest parse."""

    chat_id: int
    state: SessionState = SessionState.IDLE
    parsed_resume: ParsedResume | None = None
    stored_resume_path: str | None = None
    original_filename: str | None = None
    record_id: int | None = None
    duplicate_decision: DuplicateDecision | None = None
    correction_text: str | None = None


class SessionStore:
    """Async-safe in-memory session store."""

    def __init__(self) -> None:
        self._sessions: dict[int, UserParseSession] = {}
        self._lock = Lock()

    async def get(self, chat_id: int) -> UserParseSession:
        """Return an existing session or create a new idle one."""

        async with self._lock:
            session = self._sessions.get(chat_id)
            if session is None:
                session = UserParseSession(chat_id=chat_id)
                self._sessions[chat_id] = session
            return session

    async def set(self, session: UserParseSession) -> None:
        """Store a session."""

        async with self._lock:
            self._sessions[session.chat_id] = session

    async def clear(self, chat_id: int) -> None:
        """Remove one user's session."""

        async with self._lock:
            self._sessions.pop(chat_id, None)
