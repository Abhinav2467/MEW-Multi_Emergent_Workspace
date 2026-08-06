"""Prompts for Gemini resume parsing and rescan."""

from __future__ import annotations

import json

from backend.models.schemas import ParsedProfile


def build_parse_prompt(raw_text: str, *, filename: str | None = None) -> str:
    return (
        "You are a resume parsing engine. Extract a structured candidate profile from the "
        "resume text below. Return ONLY JSON matching the provided schema.\n"
        "Rules:\n"
        "1. Do not invent facts that are not present in the resume.\n"
        "2. skills: extract a clean, de-duplicated list of technical and domain skills "
        "(languages, frameworks, tools, cloud, ML).\n"
        "3. experience_years: estimate total professional experience as a number if possible, else null.\n"
        "4. current_role: most recent job title if present.\n"
        "5. preferred_roles: 2-5 roles the candidate is clearly suited for based on the resume.\n"
        "6. contact: extract name, email, phone, location (city/state/country), linkedin, and links.\n"
        "7. experience: list each role with title, company, location, dates, and description bullets.\n"
        "8. education: institution, degree, field_of_study, and dates when available.\n"
        "9. raw_text: omit or leave empty (the server will attach the source text).\n\n"
        f"Source filename: {filename or 'unknown'}\n\n"
        f"Resume text:\n{raw_text}"
    )


def build_rescan_prompt(current: ParsedProfile, raw_text: str | None = None) -> str:
    dump = current.model_dump(mode="json")
    dump.pop("raw_text", None)
    if "metadata" in dump:
        dump.pop("metadata", None)
    current_json = json.dumps(dump, indent=2, sort_keys=True)
    text = raw_text or current.raw_text or ""
    return (
        "You re-parse a resume into structured JSON. Return ONLY JSON matching the schema. "
        "Use the resume text as the source of truth. Improve incomplete or incorrect fields "
        "from the current parse without inventing details. Omit raw_text.\n\n"
        f"Current parsed JSON:\n{current_json}\n\n"
        f"Resume text:\n{text}"
    )
