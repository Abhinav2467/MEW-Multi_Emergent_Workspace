from resume_parser_agent.bot.formatters import (
    format_error_message,
    format_json_block,
    format_summary,
)
from resume_parser_agent.errors import UnsupportedFileTypeError
from resume_parser_agent.schemas import ContactInfo, ParsedResume


def test_format_summary_and_json_block() -> None:
    resume = ParsedResume(
        contact=ContactInfo(name="Jane Doe", email="jane@example.com"),
        skills=["Python"],
        raw_text="secret raw resume text",
    )

    summary = format_summary(resume)
    assert "Parsing Complete!" in summary
    assert "Name: Jane Doe" in summary
    assert "Email: jane@example.com" in summary
    assert "Phone: None" in summary
    assert "Skills: Python" in summary
    json_block = format_json_block(resume)
    assert "```json" in json_block
    assert "secret raw resume text" not in json_block
    assert "omitted from Telegram reply" in json_block


def test_format_json_block_is_bounded_for_large_resumes() -> None:
    resume = ParsedResume(
        contact=ContactInfo(name="Jane Doe", email="jane@example.com"),
        skills=[f"Skill {index}" for index in range(600)],
        raw_text="x" * 100_000,
    )

    assert len(format_json_block(resume)) < 3200


def test_format_error_message_uses_known_user_message() -> None:
    assert format_error_message(UnsupportedFileTypeError()) == "Please upload a PDF or DOCX resume."
    assert "Something went wrong" in format_error_message(RuntimeError("boom"))
