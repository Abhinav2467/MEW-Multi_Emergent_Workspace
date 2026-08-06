"""Prompts for Gemini correction flow."""

import json

from resume_parser_agent.schemas import CorrectionRequest


def build_correction_prompt(request: CorrectionRequest) -> str:
    """Build a concise correction prompt with the current JSON and user feedback."""

    current_json = json.dumps(
        request.current_resume.model_dump(mode="json"),
        indent=2,
        sort_keys=True,
    )
    return (
        "You correct parsed resume JSON. Return only JSON matching the provided schema. "
        "Preserve correct existing fields, apply the user's correction, and do not invent "
        "details that are not present in the current parse or user correction. "
        "If the user says a field is wrong but does not provide the corrected value, "
        "inspect the resume raw_text in the current JSON and correct the field only when "
        "the right value is clearly present there. If you cannot confidently identify the "
        "right value, return the current JSON unchanged.\n\n"
        f"Resume ID: {request.resume_id}\n\n"
        f"Current parsed JSON:\n{current_json}\n\n"
        f"User correction:\n{request.correction_text}"
    )
