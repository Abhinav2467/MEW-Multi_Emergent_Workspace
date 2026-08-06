"""Helper module to synchronize parsed profile data to autofill_agent/backend/data/profile.json."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from backend.models.schemas import ParsedProfile

PROFILE_JSON_PATH = Path(__file__).resolve().parent.parent.parent / "autofill_agent" / "backend" / "data" / "profile.json"


def infer_name_from_email_or_filename(email: str | None, filename: str | None) -> str:
    if email and "@" in email:
        handle = email.split("@")[0]
        # Remove numbers or special tags
        cleaned = re.sub(r"[\d_.-]+", " ", handle).strip()
        if cleaned:
            return " ".join(word.capitalize() for word in cleaned.split())
    if filename:
        stem = Path(filename).stem
        cleaned = re.sub(r"[\d_.-]+", " ", stem).strip()
        if cleaned and len(cleaned) > 2:
            return " ".join(word.capitalize() for word in cleaned.split()[:3])
    return "Candidate"


def format_profile_to_dict(profile: ParsedProfile, resume_file_path: str | None = None) -> dict[str, Any]:
    contact = profile.contact
    raw_name = contact.name or ""
    if not raw_name or raw_name.lower() in {"candidate", "unknown", "none"}:
        raw_name = infer_name_from_email_or_filename(contact.email, resume_file_path)

    name_parts = raw_name.strip().split(" ")
    first_name = name_parts[0] if name_parts else ""
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

    github_url = getattr(contact, "github", "") or ""
    portfolio_url = getattr(contact, "portfolio", "") or ""
    location = getattr(contact, "location", "") or ""
    if not location and profile.experience:
        for exp in profile.experience:
            if exp.location:
                location = exp.location
                break
    if not location:
        location = "Bengaluru, India"

    if not github_url or not portfolio_url:
        for link in (contact.links or []):
            if "github.com" in link.lower() and not github_url:
                github_url = link
            elif not portfolio_url:
                portfolio_url = link

    if not github_url and profile.raw_text:
        gh_match = re.search(r"(?:https?://)?(?:www\.)?github\.com/([A-Za-z0-9_.-]+)", profile.raw_text, re.I)
        if gh_match:
            github_url = f"https://github.com/{gh_match.group(1).rstrip('.,)')}"

    return {
        "personal": {
            "first_name": first_name,
            "last_name": last_name,
            "full_name": raw_name,
            "email": contact.email or "",
            "phone": contact.phone or "",
            "linkedin_url": contact.linkedin or "",
            "github_url": github_url,
            "portfolio_url": portfolio_url,
            "location": location,
        },
        "professional": {
            "current_title": profile.current_role or "Full Stack AI Engineer",
            "primary_skills": profile.skills or [],
            "years_experience": profile.experience_years or 0,
            "summary": profile.raw_text or "",
        },
        "custom_qa": {
            "willing_to_relocate": "Yes",
            "work_authorization": "Authorized to work",
        },
        "resume_file_path": resume_file_path or "",
        "parsed_profile": profile.model_dump(mode="json"),
    }


def sync_profile_to_autofill_json(profile: ParsedProfile, resume_file_path: str | None = None) -> dict[str, Any]:
    formatted = format_profile_to_dict(profile, resume_file_path=resume_file_path)
    try:
        PROFILE_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(PROFILE_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(formatted, f, indent=2)
    except Exception as err:
        print(f"[Warning] Failed to sync profile.json: {err}")
    return formatted
