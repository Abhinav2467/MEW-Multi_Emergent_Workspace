"""Safe local storage for uploaded resume files."""

from dataclasses import dataclass
from pathlib import Path
import re
from shutil import copy2
from uuid import uuid4

from resume_parser_agent.errors import ResumeStorageError, UnsupportedFileTypeError


ALLOWED_RESUME_EXTENSIONS = {".pdf", ".docx"}
SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_-]+")
UNDERSCORE_RE = re.compile(r"_+")


@dataclass(frozen=True, slots=True)
class StoredResumeFile:
    """Metadata for a locally stored resume file."""

    original_filename: str
    stored_filename: str
    relative_path: str
    absolute_path: Path


def store_resume_file(
    source_path: str | Path,
    *,
    person_name: str | None,
    storage_dir: str | Path,
) -> StoredResumeFile:
    """Copy an uploaded PDF/DOCX into the configured local resume directory."""

    source = Path(source_path)
    extension = source.suffix.lower()
    if extension not in ALLOWED_RESUME_EXTENSIONS:
        raise UnsupportedFileTypeError(
            context={"filename": source.name, "extension": extension or "<none>"}
        )
    if not source.is_file():
        raise ResumeStorageError(
            "Resume source file does not exist.",
            context={"path": str(source)},
        )

    root = Path(storage_dir)
    root.mkdir(parents=True, exist_ok=True)
    resolved_root = root.resolve()

    safe_name = sanitize_person_name(person_name)
    stored_filename = f"{safe_name}__{uuid4().hex}{extension}"
    destination = (resolved_root / stored_filename).resolve()
    if not _is_relative_to(destination, resolved_root):
        raise ResumeStorageError(
            "Refusing to store resume outside storage directory.",
            context={"destination": str(destination)},
        )

    copy2(source, destination)
    return StoredResumeFile(
        original_filename=source.name,
        stored_filename=stored_filename,
        relative_path=stored_filename,
        absolute_path=destination,
    )


def sanitize_person_name(person_name: str | None) -> str:
    """Return a filesystem-safe person name, or Unknown when unavailable."""

    if not person_name or not person_name.strip():
        return "Unknown"
    sanitized = SAFE_NAME_RE.sub("_", person_name.strip())
    sanitized = UNDERSCORE_RE.sub("_", sanitized).strip("_.-")
    return sanitized or "Unknown"


def resolve_stored_resume_path(relative_path: str | Path, storage_dir: str | Path) -> Path:
    """Resolve a stored resume path and reject traversal outside storage_dir."""

    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ResumeStorageError(
            "Stored resume path must be relative to the resume storage directory.",
            context={"relative_path": str(relative_path)},
        )
    if relative.suffix.lower() not in ALLOWED_RESUME_EXTENSIONS:
        raise UnsupportedFileTypeError(
            context={"filename": relative.name, "extension": relative.suffix or "<none>"}
        )

    root = Path(storage_dir).resolve()
    resolved = (root / relative).resolve()
    if not _is_relative_to(resolved, root):
        raise ResumeStorageError(
            "Stored resume path escapes the resume storage directory.",
            context={"relative_path": str(relative_path)},
        )
    return resolved


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True
