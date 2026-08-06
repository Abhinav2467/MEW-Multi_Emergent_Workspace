"""Telegram message formatting helpers."""

import json

from resume_parser_agent.errors import ResumeParserError
from resume_parser_agent.schemas import ParsedResume


MAX_TELEGRAM_JSON_CHARS = 2800


def format_summary(resume: ParsedResume) -> str:
    """Return a compact Telegram-friendly parsed resume summary."""

    contact = resume.contact
    skills = ", ".join(resume.skills) if resume.skills else "None"
    lines = [
        "Parsing Complete!",
        "",
        f"Name: {contact.name or 'Unknown'}",
        f"Email: {contact.email or 'None'}",
        f"Phone: {contact.phone or 'None'}",
        f"Skills: {skills}",
    ]
    return "\n".join(lines)


def format_json_block(resume: ParsedResume) -> str:
    """Return bounded parsed resume JSON in a Telegram-friendly code block."""

    payload = resume.model_dump(mode="json")
    if payload.get("raw_text"):
        payload["raw_text"] = "<omitted from Telegram reply; available in dashboard/database>"
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    if len(rendered) > MAX_TELEGRAM_JSON_CHARS:
        rendered = rendered[:MAX_TELEGRAM_JSON_CHARS].rstrip() + "\n..."
    return "```json\n" + rendered + "\n```"


def format_error_message(error: Exception) -> str:
    """Return a graceful user-facing error message."""

    if isinstance(error, ResumeParserError):
        return error.user_message
    return "Something went wrong while processing the resume. Please try again."
