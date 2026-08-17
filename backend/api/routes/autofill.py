"""Autofill and Application Tracker routes connected to SQLite parsed profile storage."""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite
from fastapi import APIRouter, Depends, Query

from autofill_agent.backend.agents.autofill_agent import match_dom_fields_with_ai
from autofill_agent.backend.schemas.applications import ApplicationLogItem, ApplicationLogResponse
from autofill_agent.backend.schemas.autofill import EventHints, FuzzyMatchRequest
from backend.models.schemas import ParsedProfile
from backend.storage.database import get_db
from backend.storage.profile_sync import PROFILE_JSON_PATH, sync_profile_to_autofill_json
from backend.storage.repositories import ProfileRepository

router = APIRouter(tags=["autofill"])

APPS_FILE = Path(__file__).resolve().parent.parent.parent.parent / "autofill_agent" / "backend" / "data" / "applications.json"


def profile_to_autofill_data(profile: ParsedProfile) -> dict[str, Any]:
    contact = profile.contact
    name_parts = (contact.name or "").strip().split(" ") if contact.name else ["", ""]
    first_name = name_parts[0] if name_parts else ""
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

    github_url = getattr(contact, "github", "") or ""
    portfolio_url = getattr(contact, "portfolio", "") or ""
    location = getattr(contact, "location", "") or ""

    if not github_url or not portfolio_url:
        for link in (contact.links or []):
            if "github.com" in link.lower() and not github_url:
                github_url = link
            elif not portfolio_url:
                portfolio_url = link

    return {
        "personal": {
            "first_name": first_name,
            "last_name": last_name,
            "full_name": contact.name or "",
            "email": contact.email or "",
            "phone": contact.phone or "",
            "linkedin_url": contact.linkedin or "",
            "github_url": github_url,
            "portfolio_url": portfolio_url,
            "location": location,
        },
        "professional": {
            "current_title": profile.current_role or "",
            "primary_skills": profile.skills or [],
            "years_experience": profile.experience_years or 0,
            "summary": profile.raw_text or "",
        },
        "custom_qa": {
            "willing_to_relocate": "Yes",
            "work_authorization": "Authorized to work",
        },
        "parsed_profile": profile.model_dump(),
    }


async def _get_active_profile_data(
    conn: aiosqlite.Connection,
    profile_id: int | None = None,
    user_id: int | None = None,
) -> dict[str, Any]:
    prof_repo = ProfileRepository(conn)
    record = None
    if profile_id:
        record = await prof_repo.get(profile_id)
    elif user_id:
        record = await prof_repo.get_latest_for_user(user_id)

    if record:
        parsed_profile = prof_repo.parse_profile(record)
        data = sync_profile_to_autofill_json(parsed_profile, resume_file_path=record.get("resume_file_path"))
        return data

    # Default active candidate profile query (check profile.json first)
    if PROFILE_JSON_PATH.exists():
        try:
            with open(PROFILE_JSON_PATH, "r", encoding="utf-8") as f:
                cached = json.load(f)
                name = cached.get("personal", {}).get("full_name") or ""
                email = cached.get("personal", {}).get("email") or ""
                if (name and name != "Candidate") or email:
                    return cached
        except Exception:
            pass

    record = await prof_repo.get_latest_for_user(user_id) if user_id else None
    if record:
        parsed_profile = prof_repo.parse_profile(record)
        data = sync_profile_to_autofill_json(parsed_profile, resume_file_path=record.get("resume_file_path"))
        return data

    return {
        "personal": {
            "first_name": "",
            "last_name": "",
            "full_name": "",
            "email": "",
            "phone": "",
            "linkedin_url": "",
            "github_url": "",
            "portfolio_url": "",
            "location": "",
        },
        "professional": {
            "current_title": "",
            "primary_skills": [],
            "years_experience": 0,
            "summary": "",
        },
        "custom_qa": {
            "willing_to_relocate": "Yes",
            "work_authorization": "Authorized to work",
        },
    }


def load_applications() -> list[dict[str, Any]]:
    if not APPS_FILE.exists():
        return []
    try:
        with open(APPS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []


def save_applications(apps: list[dict[str, Any]]) -> None:
    APPS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(APPS_FILE, "w") as f:
        json.dump(apps, f, indent=2)


@router.get("/api/v1/autofill-payload")
async def get_autofill_payload(
    profile_id: int | None = Query(None),
    user_id: int | None = Query(None),
    conn: aiosqlite.Connection = Depends(get_db),
):
    profile_data = await _get_active_profile_data(conn, profile_id=profile_id, user_id=user_id)
    payload = profile_data.copy()
    payload["event_hints"] = EventHints().model_dump()
    return {"status": "success", "data": payload}


@router.get("/autofill/preview")
async def get_autofill_preview(
    profile_id: int | None = Query(None),
    user_id: int | None = Query(None),
    conn: aiosqlite.Connection = Depends(get_db),
):
    profile_data = await _get_active_profile_data(conn, profile_id=profile_id, user_id=user_id)
    return {"status": "success", "data": {"active_profile": profile_data}}


@router.post("/api/v1/autofill-payload/match")
async def match_autofill_fields(
    request: FuzzyMatchRequest,
    profile_id: int | None = Query(None),
    user_id: int | None = Query(None),
    conn: aiosqlite.Connection = Depends(get_db),
):
    profile_data = await _get_active_profile_data(conn, profile_id=profile_id, user_id=user_id)
    match_response = match_dom_fields_with_ai(request.fields, profile_data)
    return {"status": "success", "data": match_response.model_dump()}


@router.get("/api/v1/applications", response_model=ApplicationLogResponse)
async def get_applications():
    apps = load_applications()
    return ApplicationLogResponse(data=[ApplicationLogItem(**item) for item in apps])


@router.post("/api/v1/applications/log")
async def log_application(item: ApplicationLogItem):
    apps = load_applications()
    item.id = f"app_{secrets.token_hex(6)}"
    item.timestamp = datetime.now(timezone.utc).isoformat()

    app_dict = item.model_dump()
    apps.append(app_dict)
    save_applications(apps)
    return {"status": "success", "data": app_dict}


@router.post("/api/v1/sync-profile")
async def sync_profile_data(payload: dict[str, Any]):
    """Save and sync candidate profile data to autofill_agent/backend/data/profile.json."""
    existing = {}
    if PROFILE_JSON_PATH.exists():
        try:
            with open(PROFILE_JSON_PATH, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            pass

    personal = payload.get("personal", {})
    professional = payload.get("professional", {})

    full_name = personal.get("full_name") or personal.get("name") or existing.get("personal", {}).get("full_name") or "Candidate"
    name_parts = full_name.strip().split(" ")
    first_name = name_parts[0] if name_parts else ""
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

    synced_data = {
        "personal": {
            "first_name": first_name,
            "last_name": last_name,
            "full_name": full_name,
            "email": personal.get("email") or existing.get("personal", {}).get("email") or "",
            "phone": personal.get("phone") or existing.get("personal", {}).get("phone") or "",
            "linkedin_url": personal.get("linkedin_url") or existing.get("personal", {}).get("linkedin_url") or "",
            "github_url": personal.get("github_url") or existing.get("personal", {}).get("github_url") or "",
            "portfolio_url": personal.get("portfolio_url") or existing.get("personal", {}).get("portfolio_url") or "",
            "location": personal.get("location") or existing.get("personal", {}).get("location") or "Bengaluru, India",
        },
        "professional": {
            "current_title": professional.get("current_title") or existing.get("professional", {}).get("current_title") or "Full Stack AI Engineer",
            "primary_skills": professional.get("primary_skills") or payload.get("skills") or existing.get("professional", {}).get("primary_skills") or [],
            "years_experience": professional.get("years_experience") or existing.get("professional", {}).get("years_experience") or 0,
            "summary": professional.get("summary") or existing.get("professional", {}).get("summary") or "",
        },
        "custom_qa": {
            "willing_to_relocate": "Yes",
            "work_authorization": "Authorized to work",
        },
        "resume_file_path": payload.get("resume_file_path") or existing.get("resume_file_path") or "",
    }

    try:
        PROFILE_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(PROFILE_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(synced_data, f, indent=2)
    except Exception as err:
        print(f"[Warning] Failed to write sync profile: {err}")

    return {"status": "success", "data": synced_data}


@router.get("/api/v1/extension/download")
async def download_extension_package():
    """Package autofill_agent/extension into a downloadable .zip for 1-click install."""
    import tempfile
    import zipfile
    from fastapi.responses import FileResponse

    ext_dir = Path(__file__).resolve().parent.parent.parent.parent / "autofill_agent" / "extension"
    if not ext_dir.exists():
        return {"status": "error", "message": "Extension directory not found"}

    tmp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    zip_path = Path(tmp_zip.name)
    tmp_zip.close()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in ext_dir.rglob("*"):
            if file.is_file() and not file.name.startswith("."):
                arcname = file.relative_to(ext_dir)
                zf.write(file, arcname)

    return FileResponse(
        path=str(zip_path),
        filename="AutoApply_Chrome_Extension.zip",
        media_type="application/zip",
    )


@router.post("/api/v1/extension/launch")
async def launch_chrome_with_extension():
    """Automatically launch Chrome with the AutoApply extension pre-loaded."""
    import os
    import platform
    import subprocess

    ext_dir = (Path(__file__).resolve().parent.parent.parent.parent / "autofill_agent" / "extension").resolve()
    if not ext_dir.exists():
        return {"status": "error", "message": f"Extension directory not found at {ext_dir}"}

    system = platform.system().lower()
    try:
        if "darwin" in system:
            subprocess.Popen([
                "open", "-a", "Google Chrome",
                "--args", f"--load-extension={ext_dir}"
            ])
            return {"status": "success", "message": "Launched Chrome with AutoApply Extension pre-loaded!"}
        elif "windows" in system:
            subprocess.Popen(f'start chrome --load-extension="{ext_dir}"', shell=True)
            return {"status": "success", "message": "Launched Chrome with AutoApply Extension pre-loaded!"}
        else:
            subprocess.Popen(["google-chrome", f"--load-extension={ext_dir}"])
            return {"status": "success", "message": "Launched Chrome with AutoApply Extension pre-loaded!"}
    except Exception as exc:
        return {"status": "error", "message": f"Could not auto-launch Chrome: {exc}"}


@router.get("/api/v1/extension/download")
async def download_extension_package():
    """Package autofill_agent/extension into a downloadable .zip for 1-click install."""
    import tempfile
    import zipfile
    from fastapi.responses import FileResponse

    ext_dir = Path(__file__).resolve().parent.parent.parent.parent / "autofill_agent" / "extension"
    if not ext_dir.exists():
        return {"status": "error", "message": "Extension directory not found"}

    tmp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    zip_path = Path(tmp_zip.name)
    tmp_zip.close()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in ext_dir.rglob("*"):
            if file.is_file() and not file.name.startswith("."):
                arcname = file.relative_to(ext_dir)
                zf.write(file, arcname)

    return FileResponse(
        path=str(zip_path),
        filename="AutoApply_Chrome_Extension.zip",
        media_type="application/zip",
    )


@router.post("/api/v1/extension/launch")
async def launch_chrome_with_extension():
    """Automatically launch Chrome with the AutoApply extension pre-loaded."""
    import os
    import platform
    import subprocess

    ext_dir = (Path(__file__).resolve().parent.parent.parent.parent / "autofill_agent" / "extension").resolve()
    if not ext_dir.exists():
        return {"status": "error", "message": f"Extension directory not found at {ext_dir}"}

    system = platform.system().lower()
    try:
        if "darwin" in system:
            subprocess.Popen([
                "open", "-a", "Google Chrome",
                "--args", f"--load-extension={ext_dir}"
            ])
            return {"status": "success", "message": "Launched Chrome with AutoApply Extension pre-loaded!"}
        elif "windows" in system:
            subprocess.Popen(f'start chrome --load-extension="{ext_dir}"', shell=True)
            return {"status": "success", "message": "Launched Chrome with AutoApply Extension pre-loaded!"}
        else:
            subprocess.Popen(["google-chrome", f"--load-extension={ext_dir}"])
            return {"status": "success", "message": "Launched Chrome with AutoApply Extension pre-loaded!"}
    except Exception as exc:
        return {"status": "error", "message": f"Could not auto-launch Chrome: {exc}"}
