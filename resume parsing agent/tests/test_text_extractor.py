from pathlib import Path

import pytest

from resume_parser_agent.errors import EmptyResumeError, UnsupportedFileTypeError
from resume_parser_agent.parser.text_extractor import detect_file_type, extract_text_from_file
from tests.test_parser_service import make_docx


def test_detect_file_type_accepts_pdf_and_docx() -> None:
    assert detect_file_type(Path("resume.pdf")) == "pdf"
    assert detect_file_type(Path("resume.DOCX")) == "docx"


def test_detect_file_type_rejects_other_files() -> None:
    with pytest.raises(UnsupportedFileTypeError):
        detect_file_type(Path("resume.png"))


def test_extract_text_rejects_empty_resume(tmp_path: Path) -> None:
    path = make_docx(tmp_path / "empty.docx", "")

    with pytest.raises(EmptyResumeError):
        extract_text_from_file(path)
