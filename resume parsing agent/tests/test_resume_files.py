from pathlib import Path

import pytest

from resume_parser_agent.errors import ResumeStorageError, UnsupportedFileTypeError
from resume_parser_agent.storage.resume_files import (
    resolve_stored_resume_path,
    sanitize_person_name,
    store_resume_file,
)


def make_source_resume(path: Path) -> Path:
    path.write_bytes(b"resume bytes")
    return path


def test_store_resume_file_uses_sanitized_name_plus_uuid(tmp_path: Path) -> None:
    source = make_source_resume(tmp_path / "upload.pdf")
    storage_dir = tmp_path / "resumes"

    stored = store_resume_file(
        source,
        person_name="Jane A. Doe",
        storage_dir=storage_dir,
    )

    assert stored.original_filename == "upload.pdf"
    assert stored.stored_filename.startswith("Jane_A_Doe__")
    assert stored.stored_filename.endswith(".pdf")
    assert stored.relative_path == stored.stored_filename
    assert stored.absolute_path.read_bytes() == b"resume bytes"
    assert stored.absolute_path.parent == storage_dir.resolve()


def test_repeated_names_do_not_collide(tmp_path: Path) -> None:
    source = make_source_resume(tmp_path / "upload.docx")
    storage_dir = tmp_path / "resumes"

    first = store_resume_file(source, person_name="Jane Doe", storage_dir=storage_dir)
    second = store_resume_file(source, person_name="Jane Doe", storage_dir=storage_dir)

    assert first.stored_filename != second.stored_filename
    assert first.absolute_path.exists()
    assert second.absolute_path.exists()


def test_missing_name_uses_unknown(tmp_path: Path) -> None:
    source = make_source_resume(tmp_path / "upload.pdf")

    stored = store_resume_file(source, person_name=None, storage_dir=tmp_path / "resumes")

    assert stored.stored_filename.startswith("Unknown__")


def test_unsafe_extension_is_rejected(tmp_path: Path) -> None:
    source = make_source_resume(tmp_path / "upload.exe")

    with pytest.raises(UnsupportedFileTypeError):
        store_resume_file(source, person_name="Jane Doe", storage_dir=tmp_path / "resumes")


def test_missing_source_file_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ResumeStorageError):
        store_resume_file(
            tmp_path / "missing.pdf",
            person_name="Jane Doe",
            storage_dir=tmp_path / "resumes",
        )


def test_resolve_stored_resume_path_rejects_traversal(tmp_path: Path) -> None:
    storage_dir = tmp_path / "resumes"

    with pytest.raises(ResumeStorageError):
        resolve_stored_resume_path("../secret.pdf", storage_dir)


def test_resolve_stored_resume_path_stays_inside_storage_dir(tmp_path: Path) -> None:
    storage_dir = tmp_path / "resumes"

    resolved = resolve_stored_resume_path("Jane_Doe__abc.pdf", storage_dir)

    assert resolved == (storage_dir / "Jane_Doe__abc.pdf").resolve()


def test_sanitize_person_name_falls_back_to_unknown() -> None:
    assert sanitize_person_name("...") == "Unknown"
