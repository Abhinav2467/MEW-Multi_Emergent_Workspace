"""Storage record models."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class ResumeRecord:
    """Persisted parsed resume row."""

    id: int
    telegram_user_id: int
    person_name: str
    target_role: str | None
    parsed_json: dict[str, Any]
    version_number: int
    duplicate_status: str
    text_hash: str
    vector_indexing_status: str
    original_filename: str
    local_file_path: str
    created_at: datetime
    updated_at: datetime
