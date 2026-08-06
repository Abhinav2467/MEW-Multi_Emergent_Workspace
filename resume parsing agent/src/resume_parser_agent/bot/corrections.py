"""Local correction parsing for Telegram feedback."""

import re

from resume_parser_agent.schemas import ParsedResume


NAME_PATTERNS = (
    re.compile(r"\bmy name is\s+(.+)$", re.IGNORECASE),
    re.compile(r"\bname\s*(?:is|:)\s+(.+)$", re.IGNORECASE),
)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE_PATTERN = re.compile(r"\bphone\s*(?:is|:)\s+(.+)$", re.IGNORECASE)
PHONE_WORD_RE = re.compile(r"\b(?:phone|phone no|phone number|mobile|contact)\b", re.IGNORECASE)
WRONG_WORD_RE = re.compile(r"\b(?:wrong|incorrect|not correct|bad|invalid)\b", re.IGNORECASE)


def apply_local_correction(resume: ParsedResume, correction_text: str) -> ParsedResume | None:
    """Apply simple name/email/phone corrections without an LLM."""

    updated = resume.model_copy(deep=True)
    changed = False

    name = _extract_name(correction_text)
    if name:
        updated.contact.name = name
        changed = True

    email_match = EMAIL_RE.search(correction_text)
    if email_match:
        updated.contact.email = email_match.group(0)
        changed = True

    phone_match = PHONE_PATTERN.search(correction_text)
    if phone_match:
        updated.contact.phone = phone_match.group(1).strip(" .")
        changed = True

    return updated if changed else None


def correction_prompt_for(correction_text: str) -> str:
    """Build a targeted correction prompt from vague feedback."""

    fields = _requested_fields(correction_text)
    if not fields:
        return (
            "Please send the corrected detail like `My name is Jane Doe`, "
            "`Email: jane@example.com`, or `Phone: +91 ...`."
        )

    examples = {
        "name": "`My name is Jane Doe`",
        "email": "`Email: jane@example.com`",
        "phone": "`Phone: +91 98765 43210`",
    }
    requested = " and ".join(fields)
    example_text = " and ".join(examples[field] for field in fields)
    return f"Please send the corrected {requested} like {example_text}."


def _extract_name(correction_text: str) -> str | None:
    for pattern in NAME_PATTERNS:
        match = pattern.search(correction_text.strip())
        if match:
            candidate = match.group(1).strip(" .")
            if _looks_like_vague_value(candidate):
                return None
            return candidate
    return None


def _looks_like_vague_value(value: str) -> bool:
    return bool(WRONG_WORD_RE.search(value) or PHONE_WORD_RE.search(value) or EMAIL_RE.search(value))


def _requested_fields(correction_text: str) -> list[str]:
    text = correction_text.strip()
    if not WRONG_WORD_RE.search(text):
        return []

    fields: list[str] = []
    lowered = text.lower()
    if "name" in lowered:
        fields.append("name")
    if "email" in lowered or "mail" in lowered:
        fields.append("email")
    if PHONE_WORD_RE.search(text):
        fields.append("phone")
    return fields
