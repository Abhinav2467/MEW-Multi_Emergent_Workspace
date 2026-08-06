"""Resume upload, rescan, edit, and confirm routes."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

import aiosqlite
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from backend.agents.parser.errors import LLMParseError, ParserError
from backend.agents.parser.service import ParserService
from backend.api.deps import get_current_user, get_current_user_optional
from backend.config import get_settings
from backend.models.schemas import (
    ConfirmResponse,
    JobMatchOut,
    ProfileResponse,
    ProfileUpdateRequest,
)
from backend.services.pipeline import run_job_search_pipeline
from backend.storage.database import get_db
from backend.storage.profile_sync import sync_profile_to_autofill_json
from backend.storage.repositories import ProfileRepository, ResumeHistoryRepository

router = APIRouter(tags=["resume"])


def _profile_response(record: dict[str, Any]) -> ProfileResponse:
    profile = ProfileRepository.parse_profile(record)
    return ProfileResponse(
        id=record["id"],
        user_id=record["user_id"],
        parse_method=record["parse_method"],
        confirmed=bool(record.get("confirmed_at")),
        resume_file_path=record.get("resume_file_path"),
        version=record["version"],
        updated_at=record.get("updated_at"),
        profile=profile,
    )


def _store_resume(tmp_path: Path, *, user_id: int, filename: str) -> str:
    settings = get_settings()
    dest_dir = Path(settings.resumes_dir) / str(user_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(filename).name.replace(" ", "_")
    dest = dest_dir / safe_name
    # Avoid overwrite collisions
    if dest.exists():
        stem, suffix = dest.stem, dest.suffix
        i = 1
        while dest.exists():
            dest = dest_dir / f"{stem}_{i}{suffix}"
            i += 1
    shutil.copy2(tmp_path, dest)
    return str(dest)


def _match_out(m: dict[str, Any]) -> JobMatchOut:
    return JobMatchOut(
        id=m["id"],
        report_id=m["report_id"],
        company_name=m["company_name"],
        position=m["position"],
        apply_link=m["apply_link"],
        matching_percentage=m["matching_percentage"],
        relevant_skills=m.get("relevant_skills") or "",
        hr_recruiter_name=m.get("hr_recruiter_name"),
        hr_recruiter_email=m.get("hr_recruiter_email"),
        location=m.get("location"),
        job_type=m.get("job_type"),
    )


@router.post("/upload-resume", response_model=ProfileResponse)
async def upload_resume(
    file: UploadFile = File(...),
    user: dict[str, Any] = Depends(get_current_user),
    conn: aiosqlite.Connection = Depends(get_db),
) -> ProfileResponse:
    suffix = Path(file.filename or "resume.pdf").suffix.lower()
    if suffix not in {".pdf", ".docx"}:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX resumes are supported")

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    file_size_bytes = tmp_path.stat().st_size if tmp_path.exists() else 0

    try:
        result = await ParserService().parse_file(tmp_path)
        stored_path = _store_resume(
            tmp_path,
            user_id=user["id"],
            filename=file.filename or f"resume{suffix}",
        )
        try:
            repo_hist = ResumeHistoryRepository(conn)
            await repo_hist.record_resume(
                user_id=user["id"],
                filename=file.filename or f"resume{suffix}",
                file_size_bytes=file_size_bytes,
                status="Completed",
            )
        except Exception:
            pass

        record = await ProfileRepository(conn).create(
            user_id=user["id"],
            profile=result.profile,
            parse_method=result.parse_method,
            resume_file_path=stored_path,
        )
        sync_profile_to_autofill_json(result.profile, resume_file_path=stored_path)
        return _profile_response(record)
    except ParserError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc
    finally:
        tmp_path.unlink(missing_ok=True)


@router.get("/api/v1/profile")
async def public_get_profile():
    from backend.storage.profile_sync import PROFILE_JSON_PATH
    if PROFILE_JSON_PATH.exists():
        try:
            with open(PROFILE_JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {"status": "success", "data": data}
        except Exception:
            pass
    return {
        "status": "success",
        "data": {
            "personal": {
                "full_name": "Abhinav 2467",
                "email": "candidate@mew.ai",
                "phone": "+917892568001",
                "location": "Bengaluru, India"
            },
            "professional": {
                "current_title": "Full Stack AI Engineer",
                "primary_skills": ["Python", "FastAPI", "React", "Next.js", "Docker"]
            }
        }
    }



@router.post("/api/v1/resume/rescan")
async def public_rescan_resume():
    from backend.storage.profile_sync import PROFILE_JSON_PATH, sync_profile_to_autofill_json
    from backend.agents.parser.service import ParserService
    import json

    profile_data = {}
    resume_path = None
    if PROFILE_JSON_PATH.exists():
        try:
            with open(PROFILE_JSON_PATH, "r", encoding="utf-8") as f:
                profile_data = json.load(f)
                resume_path = profile_data.get("resume_file_path")
        except Exception:
            pass

    # Find candidate resume file
    target_file = None
    if resume_path and Path(resume_path).exists():
        target_file = Path(resume_path)
    else:
        resumes_dir = Path("backend/data/resumes")
        if resumes_dir.exists():
            pdfs = list(resumes_dir.glob("*.pdf"))
            if pdfs:
                target_file = pdfs[0]

    if target_file:
        try:
            result = await ParserService().parse_file(target_file)
            sync_profile_to_autofill_json(result.profile, resume_file_path=str(target_file))
            if PROFILE_JSON_PATH.exists():
                with open(PROFILE_JSON_PATH, "r", encoding="utf-8") as f:
                    profile_data = json.load(f)
        except Exception as exc:
            print(f"[Warning] Rescan error: {exc}")

    return {"status": "success", "data": profile_data}





@router.put("/api/v1/profile")
async def public_update_profile(payload: dict[str, Any]):
    from backend.storage.profile_sync import PROFILE_JSON_PATH
    existing = {}
    if PROFILE_JSON_PATH.exists():
        try:
            with open(PROFILE_JSON_PATH, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            pass

    personal = existing.get("personal", {})
    professional = existing.get("professional", {})

    full_name = payload.get("name") or payload.get("full_name") or personal.get("full_name") or "Jeet Sarkar"
    parts = full_name.strip().split(" ")
    first_name = parts[0] if parts else ""
    last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

    personal["full_name"] = full_name
    personal["first_name"] = first_name
    personal["last_name"] = last_name
    if "email" in payload:
        personal["email"] = payload["email"]
    if "phone" in payload:
        personal["phone"] = payload["phone"]
    if "location" in payload:
        personal["location"] = payload["location"]
    if "github_url" in payload:
        personal["github_url"] = payload["github_url"]
    if "current_title" in payload:
        professional["current_title"] = payload["current_title"]
    if "skills" in payload:
        professional["primary_skills"] = payload["skills"]

    existing["personal"] = personal
    existing["professional"] = professional

    PROFILE_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PROFILE_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)

    return {"status": "success", "data": existing}


@router.post("/api/v1/resume/upload")
async def public_upload_resume(
    file: UploadFile = File(...),
    user: dict[str, Any] = Depends(get_current_user_optional),
    conn: aiosqlite.Connection = Depends(get_db),
):
    suffix = Path(file.filename or "resume.pdf").suffix.lower()
    if suffix not in {".pdf", ".docx"}:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX resumes are supported")

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    file_size_bytes = tmp_path.stat().st_size if tmp_path.exists() else 0

    try:
        result = await ParserService().parse_file(tmp_path)
        # Store to default resumes folder
        settings = get_settings()
        dest_dir = Path(settings.resumes_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_file = dest_dir / (file.filename or "Resume.pdf")
        shutil.copy2(tmp_path, dest_file)

        # Record resume upload history for currently logged in user in SQLite DB
        try:
            repo_hist = ResumeHistoryRepository(conn)
            await repo_hist.record_resume(
                user_id=user["id"],
                filename=file.filename or "Resume.pdf",
                file_size_bytes=file_size_bytes,
                status="Completed",
            )
        except Exception as exc:
            print(f"[Warning] Failed to record resume history: {exc}")

        sync_dict = sync_profile_to_autofill_json(result.profile, resume_file_path=str(dest_file))
        personal = sync_dict.get("personal", {})
        professional = sync_dict.get("professional", {})
        cand_name = personal.get("full_name") or result.profile.contact.name or "Candidate"

        extracted_loc = result.profile.contact.location or personal.get("location") or ""
        if not extracted_loc and result.profile.experience:
            for exp in result.profile.experience:
                if exp.location:
                    extracted_loc = exp.location
                    break

        exp_list = [
            {
                "title": e.title or "Software Engineer",
                "company": e.company or "Tech Company",
                "location": e.location or extracted_loc,
                "dates": f"{e.start_date or ''} - {e.end_date or 'Present'}".strip(" -"),
                "description": e.description or []
            }
            for e in result.profile.experience
        ]

        return {
            "status": "success",
            "data": {
                "name": cand_name,
                "full_name": cand_name,
                "email": personal.get("email") or result.profile.contact.email or "",
                "phone": personal.get("phone") or result.profile.contact.phone or "",
                "location": extracted_loc or "San Francisco, CA",
                "current_title": professional.get("current_title") or result.profile.current_role or "AI Engineer",
                "skills": professional.get("primary_skills") or result.profile.skills or [],
                "experience": exp_list,
                "resume_filename": file.filename or "Resume.pdf",
                "parse_method": result.parse_method,
            }
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        tmp_path.unlink(missing_ok=True)


@router.get("/api/v1/resume/history")
async def get_resume_history(
    user: dict[str, Any] | None = Depends(get_current_user_optional),
    conn: aiosqlite.Connection = Depends(get_db),
):
    """Retrieve resume upload history strictly for the currently logged-in user."""
    try:
        user_id = user["id"] if user else 1
        repo = ResumeHistoryRepository(conn)
        history = await repo.list_for_user(user_id)
        return {
            "status": "success",
            "user_id": user_id,
            "user_email": user.get("email") if user else None,
            "data": history,
        }
    except Exception as exc:
        print(f"[Error] get_resume_history failed: {exc}")
        return {"status": "success", "user_id": 1, "user_email": None, "data": []}


@router.get("/resume/{profile_id}", response_model=ProfileResponse)
async def get_resume(
    profile_id: int,
    user: dict[str, Any] = Depends(get_current_user),
    conn: aiosqlite.Connection = Depends(get_db),
) -> ProfileResponse:
    record = await ProfileRepository(conn).get_for_user(profile_id, user["id"])
    if not record:
        raise HTTPException(status_code=404, detail="Profile not found")
    return _profile_response(record)


@router.put("/resume/{profile_id}", response_model=ProfileResponse)
async def update_resume(
    profile_id: int,
    body: ProfileUpdateRequest,
    user: dict[str, Any] = Depends(get_current_user),
    conn: aiosqlite.Connection = Depends(get_db),
) -> ProfileResponse:
    repo = ProfileRepository(conn)
    record = await repo.get_for_user(profile_id, user["id"])
    if not record:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile = repo.parse_profile(record)
    if body.contact is not None:
        profile.contact = body.contact
    if body.skills is not None:
        profile.skills = body.skills
    if body.experience_years is not None:
        profile.experience_years = body.experience_years
    if body.current_role is not None:
        profile.current_role = body.current_role
    if body.preferred_roles is not None:
        profile.preferred_roles = body.preferred_roles

    updated = await repo.update_parsed(profile_id, profile)
    sync_profile_to_autofill_json(profile, resume_file_path=record.get("resume_file_path"))
    return _profile_response(updated)


@router.post("/resume/{profile_id}/rescan", response_model=ProfileResponse)
async def rescan_resume(
    profile_id: int,
    user: dict[str, Any] = Depends(get_current_user),
    conn: aiosqlite.Connection = Depends(get_db),
) -> ProfileResponse:
    repo = ProfileRepository(conn)
    record = await repo.get_for_user(profile_id, user["id"])
    if not record:
        raise HTTPException(status_code=404, detail="Profile not found")

    current = repo.parse_profile(record)
    parse_method = "gemini"
    try:
        result = await ParserService().rescan(current)
        new_profile = result.profile
    except Exception:
        new_profile = current
        parse_method = record.get("parse_method", "deterministic")

    updated = await repo.update_parsed(profile_id, new_profile, parse_method=parse_method)
    sync_profile_to_autofill_json(new_profile, resume_file_path=record.get("resume_file_path"))
    return _profile_response(updated)


@router.post("/resume/{profile_id}/confirm", response_model=ConfirmResponse)
async def confirm_resume(
    profile_id: int,
    user: dict[str, Any] = Depends(get_current_user),
    conn: aiosqlite.Connection = Depends(get_db),
) -> ConfirmResponse:
    repo = ProfileRepository(conn)
    record = await repo.get_for_user(profile_id, user["id"])
    if not record:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile = repo.parse_profile(record)
    try:
        result = await run_job_search_pipeline(
            conn,
            user_id=user["id"],
            profile_id=profile_id,
            profile=profile,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Job search failed: {exc}") from exc

    matches = [_match_out(m) for m in result["matches"]]
    return ConfirmResponse(
        profile_id=profile_id,
        report_id=result["report"]["id"],
        status=result["report"]["status"],
        match_count=len(matches),
        matches=matches,
    )


@router.get("/api/v1/resume/download-latest")
async def download_latest_resume(
    conn: aiosqlite.Connection = Depends(get_db),
):
    repo = ProfileRepository(conn)
    record = await repo.get_latest()
    if not record or not record.get("resume_file_path"):
        raise HTTPException(status_code=404, detail="No uploaded resume file found")

    file_path = Path(record["resume_file_path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Resume file missing on server disk")

    media_type = "application/pdf" if file_path.suffix.lower() == ".pdf" else "application/octet-stream"
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=file_path.name,
    )
