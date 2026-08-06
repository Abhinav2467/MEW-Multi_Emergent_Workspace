from pathlib import Path

import fitz
import pytest
from docx import Document

from resume_parser_agent.errors import UnsupportedFileTypeError
from resume_parser_agent.parser.service import ResumeParserService


RESUME_TEXT = """Jane Doe
jane@example.com
+1 555 123 4567
https://linkedin.com/in/janedoe

Skills
Python, FastAPI, Docker, SQL

Experience
- Built async resume parsing services.
- Improved parser latency below 300ms.

Education
State University
"""


def make_pdf(path: Path, text: str = RESUME_TEXT) -> Path:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    document.save(path)
    document.close()
    return path


def make_docx(path: Path, text: str = RESUME_TEXT) -> Path:
    document = Document()
    for line in text.splitlines():
        document.add_paragraph(line)
    document.save(path)
    return path


def test_pdf_fixture_parses_core_fields(tmp_path: Path) -> None:
    path = make_pdf(tmp_path / "resume.pdf")

    parsed = ResumeParserService().parse_file(path)

    assert parsed.contact.name == "Jane Doe"
    assert parsed.contact.email == "jane@example.com"
    assert parsed.contact.phone == "+1 555 123 4567"
    assert "Python" in parsed.skills
    assert "Fastapi" in parsed.skills
    assert parsed.experience[0].description
    assert parsed.education[0].institution == "State University"
    assert parsed.metadata.source_file_type == "pdf"


def test_docx_fixture_parses_core_fields(tmp_path: Path) -> None:
    path = make_docx(tmp_path / "resume.docx")

    parsed = ResumeParserService().parse_file(path)

    assert parsed.contact.name == "Jane Doe"
    assert parsed.contact.email == "jane@example.com"
    assert parsed.metadata.source_file_type == "docx"
    assert parsed.metadata.confidence_score > 0.7


def test_unsupported_file_fails_gracefully(tmp_path: Path) -> None:
    path = tmp_path / "resume.txt"
    path.write_text(RESUME_TEXT, encoding="utf-8")

    with pytest.raises(UnsupportedFileTypeError) as exc_info:
        ResumeParserService().parse_file(path)

    assert exc_info.value.code == "unsupported_file_type"


def test_deterministic_parse_timing_is_measured(tmp_path: Path) -> None:
    path = make_docx(tmp_path / "resume.docx")

    parsed = ResumeParserService().parse_file(path)

    timings = parsed.metadata.stage_timings_ms
    assert set(timings) == {
        "extract_text",
        "normalize_text",
        "extract_fields",
        "score_confidence",
    }
    assert sum(timings.values()) < 300
