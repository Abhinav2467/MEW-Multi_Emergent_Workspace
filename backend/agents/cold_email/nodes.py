"""LangGraph nodes for cold email outreach."""

from __future__ import annotations

from typing import Any, TypedDict

from backend.agents.cold_email.tools import (
    discover_recruiter_leads,
    execute_cold_email,
    generate_email_body,
)
from backend.agents.job_search.domain_resolver import resolve_company_domain
from backend.config import get_settings


class ColdEmailState(TypedDict, total=False):
    company: str
    role: str
    job_title: str
    location: str
    domain: str
    apply_link: str
    leads: list[dict[str, Any]]
    lead_name: str
    lead_email: str
    body: str
    subject: str
    draft_id: str
    message_id: str
    gmail_creds: dict[str, Any]
    sender_name: str
    expertise: str
    resume_path: str
    send_now: bool
    error: str


def search_recruiters(state: ColdEmailState) -> ColdEmailState:
    company = state["company"]
    apply_link = state.get("apply_link") or ""
    settings = get_settings()
    domain = state.get("domain") or resolve_company_domain(
        company, apply_link, groq_api_key=settings.groq_api_key
    )
    leads = discover_recruiter_leads(
        company,
        "Recruiter",
        domain,
        job_title=state.get("job_title") or state.get("role"),
        job_location=state.get("location"),
    )
    lead_name = ""
    lead_email = ""
    if leads:
        lead = leads[0]
        lead_name = lead.get("name") or ""
        lead_email = lead.get("email") or ""
        if lead.get("status") == "unverified_limit" and lead_email:
            # keep email but note in name if needed
            pass
    return {
        **state,
        "domain": domain,
        "leads": leads,
        "lead_name": lead_name,
        "lead_email": lead_email,
    }


def generate_body(state: ColdEmailState) -> ColdEmailState:
    if not state.get("lead_email"):
        return {**state, "error": "No recruiter email found"}
    body = generate_email_body(
        sender_name=state.get("sender_name") or "Candidate",
        expertise=state.get("expertise") or "software engineering",
        lead_name=state.get("lead_name") or "Recruiter",
        company=state["company"],
        role=state.get("role") or state.get("job_title") or "the open role",
    )
    subject = f"Inquiry: {state.get('role') or state.get('job_title') or 'Opportunity'}"
    return {**state, "body": body, "subject": subject}


def create_or_send(state: ColdEmailState) -> ColdEmailState:
    if state.get("error"):
        return state
    if not state.get("lead_email"):
        return {**state, "error": "No recruiter email found"}
    creds = state.get("gmail_creds")
    if not creds:
        return {**state, "error": "Missing Gmail credentials"}

    send_now = bool(state.get("send_now"))
    try:
        res = execute_cold_email(
            creds,
            state.get("sender_name") or "Candidate",
            state["lead_email"],
            state.get("lead_name") or "Recruiter",
            state.get("subject") or "Inquiry",
            state.get("body") or "",
            state["company"],
            state.get("role") or "",
            state.get("resume_path"),
            send_now,
        )
        if send_now:
            return {**state, "message_id": res.get("id", ""), "draft_id": ""}
        return {**state, "draft_id": res.get("id", ""), "message_id": ""}
    except Exception as exc:
        return {**state, "error": str(exc)}
