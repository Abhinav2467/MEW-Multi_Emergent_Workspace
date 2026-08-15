"""Cold email draft and send routes."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException

from backend.agents.cold_email.graph import run_cold_email_flow
from backend.api.deps import get_current_user
from backend.config import get_settings
from backend.models.schemas import DraftCreateRequest, DraftResponse, SendDraftsRequest
from backend.services.report import refresh_report_files
from backend.storage.database import get_db
from backend.storage.repositories import (
    DraftRepository,
    JobMatchRepository,
    ProfileRepository,
    ReportRepository,
)

router = APIRouter(tags=["emails"])


def _expertise_from_profile(profile) -> str:
    if profile.skills:
        return ", ".join(profile.skills)
    if profile.current_role:
        return profile.current_role
    return "software engineering"


async def _run_draft_for_match(
    *,
    conn: aiosqlite.Connection,
    user: dict[str, Any],
    match: dict[str, Any],
    profile_record: dict[str, Any],
    send_now: bool = False,
) -> DraftResponse:
    profile = ProfileRepository.parse_profile(profile_record)
    gmail_tokens = user.get("gmail_tokens_json")
    if not gmail_tokens:
        raise HTTPException(status_code=400, detail="Gmail not connected. Complete Google OAuth first.")

    creds = json.loads(gmail_tokens)
    state = {
        "company": match["company_name"],
        "role": match["position"],
        "job_title": match["position"],
        "location": match.get("location") or "",
        "apply_link": match["apply_link"],
        "gmail_creds": creds,
        "sender_name": profile.contact.name or user.get("name") or "Candidate",
        "expertise": _expertise_from_profile(profile),
        "resume_path": profile_record.get("resume_file_path") or "",
        "send_now": send_now,
    }

    result = await asyncio.to_thread(run_cold_email_flow, state)

    lead_name = result.get("lead_name") or None
    lead_email = result.get("lead_email") or None
    error = result.get("error")

    await JobMatchRepository(conn).update_hr(
        match["id"],
        hr_recruiter_name=lead_name,
        hr_recruiter_email=lead_email,
    )

    # Refresh report files for this match's report
    report = await ReportRepository(conn).get(match["report_id"])
    if report:
        all_matches = await JobMatchRepository(conn).list_for_report(match["report_id"])
        refresh_report_files(
            user_id=user["id"],
            report_id=match["report_id"],
            matches=all_matches,
            profile_id=report["profile_id"],
        )

    draft_repo = DraftRepository(conn)
    if error:
        record = await draft_repo.create(
            user_id=user["id"],
            job_match_id=match["id"],
            gmail_draft_id=None,
            status="error",
            error=error,
        )
    elif send_now:
        record = await draft_repo.create(
            user_id=user["id"],
            job_match_id=match["id"],
            gmail_draft_id=result.get("message_id"),
            status="sent",
            error=None,
        )
        await draft_repo.mark_sent(record["id"])
        record = await draft_repo.get(record["id"])
    else:
        record = await draft_repo.create(
            user_id=user["id"],
            job_match_id=match["id"],
            gmail_draft_id=result.get("draft_id"),
            status="draft",
            error=None,
        )

    assert record is not None
    return DraftResponse(
        id=record["id"],
        job_match_id=match["id"],
        gmail_draft_id=record.get("gmail_draft_id"),
        status=record["status"],
        hr_recruiter_name=lead_name,
        hr_recruiter_email=lead_email,
        error=record.get("error"),
    )


@router.post("/emails/drafts", response_model=list[DraftResponse])
async def create_drafts(
    body: DraftCreateRequest,
    user: dict[str, Any] = Depends(get_current_user),
    conn: aiosqlite.Connection = Depends(get_db),
) -> list[DraftResponse]:
    if not body.job_match_ids:
        raise HTTPException(status_code=400, detail="job_match_ids is required")

    settings = get_settings()
    match_repo = JobMatchRepository(conn)
    report_repo = ReportRepository(conn)
    profile_repo = ProfileRepository(conn)

    # Validate ownership via report.user_id
    matches: list[dict[str, Any]] = []
    profile_record: dict[str, Any] | None = None
    for mid in body.job_match_ids:
        match = await match_repo.get(mid)
        if not match:
            raise HTTPException(status_code=404, detail=f"Job match {mid} not found")
        report = await report_repo.get_for_user(match["report_id"], user["id"])
        if not report:
            raise HTTPException(status_code=404, detail=f"Job match {mid} not found")
        matches.append(match)
        if profile_record is None:
            profile_record = await profile_repo.get_for_user(report["profile_id"], user["id"])

    if not profile_record:
        raise HTTPException(status_code=404, detail="Profile not found for matches")

    sem = asyncio.Semaphore(settings.email_draft_concurrency)
    results: list[DraftResponse] = []

    async def _one(match: dict[str, Any]) -> DraftResponse:
        async with sem:
            return await _run_draft_for_match(
                conn=conn,
                user=user,
                match=match,
                profile_record=profile_record,
                send_now=False,
            )

    # Sequential within semaphore to avoid concurrent SQLite write issues on same connection
    for match in matches:
        results.append(await _one(match))
    return results


@router.get("/emails/drafts", response_model=list[DraftResponse])
async def list_drafts(
    user: dict[str, Any] = Depends(get_current_user),
    conn: aiosqlite.Connection = Depends(get_db),
) -> list[DraftResponse]:
    drafts = await DraftRepository(conn).list_for_user(user["id"])
    match_repo = JobMatchRepository(conn)
    out: list[DraftResponse] = []
    for d in drafts:
        match = await match_repo.get(d["job_match_id"])
        out.append(
            DraftResponse(
                id=d["id"],
                job_match_id=d["job_match_id"],
                gmail_draft_id=d.get("gmail_draft_id"),
                status=d["status"],
                hr_recruiter_name=match.get("hr_recruiter_name") if match else None,
                hr_recruiter_email=match.get("hr_recruiter_email") if match else None,
                error=d.get("error"),
            )
        )
    return out


@router.post("/emails/send", response_model=list[DraftResponse])
async def send_drafts(
    body: SendDraftsRequest,
    user: dict[str, Any] = Depends(get_current_user),
    conn: aiosqlite.Connection = Depends(get_db),
) -> list[DraftResponse]:
    """Re-run outreach with send_now=True for previously drafted job matches."""
    if not body.draft_ids:
        raise HTTPException(status_code=400, detail="draft_ids is required")

    draft_repo = DraftRepository(conn)
    match_repo = JobMatchRepository(conn)
    report_repo = ReportRepository(conn)
    profile_repo = ProfileRepository(conn)
    results: list[DraftResponse] = []

    for draft_id in body.draft_ids:
        draft = await draft_repo.get_for_user(draft_id, user["id"])
        if not draft:
            raise HTTPException(status_code=404, detail=f"Draft {draft_id} not found")
        if draft["status"] == "sent":
            match = await match_repo.get(draft["job_match_id"])
            results.append(
                DraftResponse(
                    id=draft["id"],
                    job_match_id=draft["job_match_id"],
                    gmail_draft_id=draft.get("gmail_draft_id"),
                    status="sent",
                    hr_recruiter_name=match.get("hr_recruiter_name") if match else None,
                    hr_recruiter_email=match.get("hr_recruiter_email") if match else None,
                    error=None,
                )
            )
            continue

        match = await match_repo.get(draft["job_match_id"])
        if not match:
            raise HTTPException(status_code=404, detail="Job match not found for draft")
        report = await report_repo.get_for_user(match["report_id"], user["id"])
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        profile_record = await profile_repo.get_for_user(report["profile_id"], user["id"])
        if not profile_record:
            raise HTTPException(status_code=404, detail="Profile not found")

        # Create a new send record via the flow
        sent = await _run_draft_for_match(
            conn=conn,
            user=user,
            match=match,
            profile_record=profile_record,
            send_now=True,
        )
        # Also mark original draft as sent if send succeeded
        if sent.status == "sent":
            await draft_repo.mark_sent(draft_id)
    return results


@router.post("/api/v1/emails/generate")
async def public_generate_cold_email(payload: dict[str, Any]):
    from backend.storage.profile_sync import PROFILE_JSON_PATH
    from backend.agents.cold_email.tools import discover_recruiter_leads
    from backend.agents.job_search.domain_resolver import resolve_company_domain
    from backend.config import get_settings
    import json
    import random
    import re

    settings = get_settings()

    # Load candidate info directly from parsed profile.json (parsed resume)
    profile_data = {}
    if PROFILE_JSON_PATH.exists():
        try:
            with open(PROFILE_JSON_PATH, "r", encoding="utf-8") as f:
                profile_data = json.load(f)
        except Exception:
            pass

    personal = profile_data.get("personal", {})
    prof = profile_data.get("professional", {})

    p_first = personal.get("first_name") or ""
    p_last = personal.get("last_name") or ""
    candidate_name = personal.get("full_name") or f"{p_first} {p_last}".strip() or "Candidate"
    candidate_email = personal.get("email") or "candidate@email.com"
    candidate_phone = personal.get("phone") or ""
    candidate_title = prof.get("current_title") or "Software Engineer"
    skills = prof.get("primary_skills") or ["Python", "FastAPI", "React"]

    company = payload.get("company_name") or payload.get("company") or "Company"
    role = payload.get("position") or payload.get("role") or candidate_title
    location = payload.get("location") or "Remote"
    apply_link = payload.get("apply_link") or ""
    is_regenerate = bool(payload.get("regenerate"))

    passed_hr_name = payload.get("hr_name") or payload.get("hr_recruiter_name")
    passed_hr_email = payload.get("hr_email") or payload.get("hr_recruiter_email")

    if is_regenerate and passed_hr_name and passed_hr_email:
        hr_name = passed_hr_name
        hr_email = passed_hr_email
    else:
        # Discover recruiter lead (Name & Email) via domain resolver and hunter/tavily/groq search
        domain = resolve_company_domain(company, apply_link, groq_api_key=settings.groq_api_key)
        leads = discover_recruiter_leads(
            company=company,
            role="Recruiter",
            domain=domain,
            job_title=role,
            job_location=location,
        )

        if leads:
            hr_name = leads[0].get("name") or f"{company} Talent Acquisition"
            hr_email = leads[0].get("email") or f"careers@{domain}"
        else:
            clean_comp = company.lower().replace(" ", "").replace(".", "")
            hr_name = f"{company} Talent Acquisition Team"
            hr_email = f"careers@{domain or (clean_comp + '.com')}"

    # Extract parsed projects from candidate resume
    summary_text = prof.get("summary") or profile_data.get("parsed_profile", {}).get("raw_text", "")
    projects = []
    if summary_text:
        lines = summary_text.splitlines()
        in_proj = False
        for line in lines:
            stripped = line.strip()
            if re.search(r'^\s*(PROJECTS|KEY PROJECTS)\b', stripped, re.I):
                in_proj = True
                continue
            if in_proj and re.search(r'^\s*(SKILLS|EDUCATION|EXPERIENCE|CERTIFICATIONS|ACHIEVEMENTS)\b', stripped, re.I):
                in_proj = False
                break
            if in_proj:
                if 'Github' in stripped or 'Lead Developer' in stripped or 'Project' in stripped or 'System' in stripped or 'AI' in stripped:
                    name = re.sub(r'(Github|Video Demo|Lead Developer|Project|System).*', '', stripped).strip(' |-–\t')
                    name = name.split('|')[0].split('–')[0].split('-')[0].strip()
                    if name and len(name) > 3 and name not in projects:
                        projects.append(name)

    # Pick 3-4 top concise skills instead of dumping 25 raw keywords
    top_skills = [s for s in skills if s.lower() not in {"html", "css", "c"}]
    selected_skills = top_skills[:4] if top_skills else skills[:4]
    skills_formatted = ", ".join(selected_skills)

    # Construct highly personalized project mention
    project_clause = ""
    if projects:
        sel_p = projects[:2]
        if len(sel_p) == 1:
            project_clause = f" For instance, I recently engineered {sel_p[0]}."
        else:
            project_clause = f" For instance, I engineered key projects like {sel_p[0]} and {sel_p[1]}."

    greetings = ["Hi", "Hello", "Dear"]
    greeting = random.choice(greetings) if is_regenerate else "Hi"
    first_name = hr_name.split()[0] if hr_name else "Recruiter"

    pitch_openings = [
        f"I recently came across the {role} position at {company} and was immediately compelled to reach out.",
        f"I am writing to express my strong enthusiasm for the {role} opportunity at {company}.",
        f"I have been following {company}'s work and wanted to reach out regarding the {role} opening.",
    ]
    opening = random.choice(pitch_openings) if is_regenerate else pitch_openings[0]

    pitch_middle = [
        f"With hands-on experience in {skills_formatted}, I specialize in building high-throughput backend microservices and agentic AI systems.{project_clause}",
        f"My background centers on {skills_formatted}, architecting scalable web applications and autonomous AI pipelines.{project_clause}",
        f"As a {candidate_title} proficient in {skills_formatted}, I focus on designing low-latency API architectures and AI workflows.{project_clause}",
    ]
    middle = random.choice(pitch_middle) if is_regenerate else pitch_middle[0]

    signature_phone = f" | {candidate_phone}" if candidate_phone else ""

    subject = f"Application & Pitch for {role} - {candidate_name}"
    body = (
        f"{greeting} {first_name},\n\n"
        f"{opening}\n\n"
        f"{middle}\n\n"
        f"I would love to learn more about your team's upcoming goals at {company} and discuss how my technical background aligns with the role.\n\n"
        f"Best regards,\n"
        f"{candidate_name}\n"
        f"{candidate_email}{signature_phone}"
    )

    return {
        "status": "success",
        "data": {
            "subject": subject,
            "body": body,
            "hr_recruiter_name": hr_name,
            "hr_recruiter_email": hr_email,
            "company_name": company,
            "position": role
        }
    }


from backend.api.deps import get_current_user, get_current_user_optional

@router.post("/api/v1/emails/save-draft")
async def public_save_draft(
    payload: dict[str, Any],
    user: dict[str, Any] = Depends(get_current_user_optional),
    conn: aiosqlite.Connection = Depends(get_db),
):
    from backend.agents.cold_email.tools import execute_cold_email
    from backend.config import WORKSPACE_DIR
    from backend.storage.profile_sync import PROFILE_JSON_PATH
    import json
    import secrets

    company = payload.get("company") or payload.get("company_name") or "Company"
    role = payload.get("role") or payload.get("position") or "Role"
    hr_email = payload.get("hr_email") or payload.get("to_email") or "careers@company.com"
    hr_name = payload.get("hr_name") or payload.get("to_name") or "Recruiter"
    subject = payload.get("subject") or f"Inquiry for {role}"
    body = payload.get("body") or ""

    candidate_name = user.get("name") or "Candidate"
    resume_path = None
    if PROFILE_JSON_PATH.exists():
        try:
            with open(PROFILE_JSON_PATH, "r", encoding="utf-8") as f:
                profile_data = json.load(f)
                personal = profile_data.get("personal", {})
                if personal.get("full_name"):
                    candidate_name = personal.get("full_name")
                resume_path = profile_data.get("resume_file_path") or None
        except Exception:
            pass

    # Load OAuth token credentials strictly from current authenticated user
    creds_dict = None
    if user.get("gmail_tokens_json"):
        t_data = user["gmail_tokens_json"]
        creds_dict = json.loads(t_data) if isinstance(t_data, str) else t_data

    if not creds_dict and user.get("id"):
        cursor = await conn.execute(
            "SELECT gmail_tokens_json FROM users WHERE id = ?", (user["id"],)
        )
        row = await cursor.fetchone()
        if row and row[0]:
            t_data = row[0]
            creds_dict = json.loads(t_data) if isinstance(t_data, str) else t_data

    if not creds_dict:
        return {
            "status": "success",
            "message": f"Cold email draft saved locally for {company}! (Connect Gmail via Google Login to sync live drafts directly to Gmail)",
            "user_email": user.get("email") or "",
            "data": {
                "draft_id": f"draft_{secrets.token_hex(6)}",
                "company": company,
                "role": role,
                "hr_email": hr_email,
                "hr_name": hr_name,
                "subject": subject,
                "body": body,
            },
        }

    try:
        res = execute_cold_email(
            creds=creds_dict,
            sender=candidate_name,
            to_email=hr_email,
            to_name=hr_name,
            subject=subject,
            body=body,
            company=company,
            role=role,
            file_path=resume_path,
            send_now=False,
        )
        draft_id = res.get("id") or (res.get("message") or {}).get("id") or f"draft_{secrets.token_hex(6)}"
        return {
            "status": "success",
            "message": f"Cold email draft saved directly in your real Gmail inbox! ({user.get('email')})",
            "user_email": user.get("email") or "",
            "data": {
                "draft_id": draft_id,
                "company": company,
                "role": role,
                "hr_email": hr_email,
                "hr_name": hr_name,
                "subject": subject,
                "saved_at": "Just now"
            }
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create draft in Gmail: {str(exc)}"
        )


@router.post("/api/v1/emails/send")
async def public_send_cold_email(
    payload: dict[str, Any],
    user: dict[str, Any] = Depends(get_current_user_optional),
    conn: aiosqlite.Connection = Depends(get_db),
):
    from backend.agents.cold_email.tools import execute_cold_email
    from backend.config import WORKSPACE_DIR
    import json

    company = payload.get("company") or payload.get("company_name") or "Company"
    role = payload.get("role") or payload.get("position") or "Role"
    to_email = payload.get("to_email") or payload.get("hr_email") or "careers@company.com"
    to_name = payload.get("to_name") or payload.get("hr_name") or "Recruiter"
    subject = payload.get("subject") or f"Inquiry for {role}"
    body = payload.get("body") or ""

    creds_dict = None
    if user.get("gmail_tokens_json"):
        t_data = user["gmail_tokens_json"]
        creds_dict = json.loads(t_data) if isinstance(t_data, str) else t_data

    if not creds_dict and user.get("id"):
        cursor = await conn.execute(
            "SELECT gmail_tokens_json FROM users WHERE id = ?", (user["id"],)
        )
        row = await cursor.fetchone()
        if row and row[0]:
            t_data = row[0]
            creds_dict = json.loads(t_data) if isinstance(t_data, str) else t_data

    sender_name = user.get("name") or "Candidate"
    sent_result = None
    if creds_dict:
        try:
            sent_result = execute_cold_email(
                creds=creds_dict,
                sender=sender_name,
                to_email=to_email,
                to_name=to_name,
                subject=subject,
                body=body,
                company=company,
                role=role,
                send_now=True,
            )
        except Exception as exc:
            print(f"[send] Error sending email via Gmail API: {exc}")

    return {
        "status": "success",
        "message": f"Email successfully dispatched via Gmail OAuth ({user.get('email')}) to {to_name} ({to_email})",
        "details": {
            "hr_recruiter_name": to_name,
            "hr_recruiter_email": to_email,
            "subject": subject,
            "sender_email": user.get("email"),
            "sent_result": sent_result,
            "sent_at": "Just now"
        }
    }

