"""Cold email tools: recruiter discovery and Gmail draft/send."""

from __future__ import annotations

import base64
import json
import os
import re
import shutil
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from pyhunter import PyHunter
from tavily import TavilyClient

from backend.config import get_settings

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send",
]


def get_gmail_service(user_creds_dict: dict[str, Any]):
    creds = Credentials.from_authorized_user_info(user_creds_dict, GMAIL_SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("gmail", "v1", credentials=creds)


def discover_recruiter_leads(
    company: str,
    role: str,
    domain: str,
    job_title: str | None = None,
    job_location: str | None = None,
) -> list[dict[str, Any]]:
    settings = get_settings()
    tavily_key = settings.tavily_api_key or os.getenv("TAVILY_API_KEY")
    hunter_key = settings.hunter_api_key or os.getenv("HUNTER_API_KEY")
    groq_key = settings.groq_api_key or os.getenv("GROQ_API_KEY")

    if not tavily_key:
        return []

    tavily = TavilyClient(api_key=tavily_key)
    hunter = PyHunter(hunter_key) if hunter_key else None

    search_query = f"{role} at {company} LinkedIn"
    if job_location:
        search_query = f"{role} at {company} {job_location} LinkedIn"

    try:
        results = tavily.search(query=search_query, search_depth="advanced", max_results=3)["results"]
    except Exception:
        return []

    search_data = [
        {"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("content", "")}
        for r in results
    ]
    recruiter_profiles: list[dict[str, Any]] = []

    def clean_json_comments(json_str: str) -> str:
        json_str = re.sub(r"(?<!http:)(?<!https:)//.*$", "", json_str, flags=re.MULTILINE)
        json_str = re.sub(r"/\*.*?\*/", "", json_str, flags=re.DOTALL)
        return json_str

    def extract_json_list(text: str) -> list[dict[str, Any]]:
        text = text.strip()
        start = text.find("[")
        end = text.rfind("]")
        if start == -1 or end == -1 or end <= start:
            raise ValueError(f"Could not parse JSON list from text: {text}")
        json_str = clean_json_comments(text[start : end + 1])
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            cleaned = re.sub(r",\s*\]", "]", json_str)
            cleaned = re.sub(r",\s*\}", "}", cleaned)
            return json.loads(cleaned)

    if groq_key:
        try:
            from langchain_groq import ChatGroq

            llm = ChatGroq(model="llama-3.1-8b-instant", groq_api_key=groq_key, temperature=0.0)
            prompt = (
                f"You are a recruiter research assistant. Analyze the following search results for a "
                f"LinkedIn recruiter at '{company}' for job '{job_title or 'N/A'}' "
                f"location '{job_location or 'N/A'}'.\n\n"
                "Identify SPECIFIC, REAL individuals who are Recruiters, Talent Acquisition, or HR "
                "at this company. Return ONLY a JSON list like "
                '[{"name": "John Doe", "linkedin": "https://linkedin.com/in/..."}]. '
                "No markdown, no comments.\n\n"
                f"Search Results:\n{json.dumps(search_data, indent=2)}"
            )
            response_text = llm.invoke(prompt).content.strip()
            recruiter_profiles = extract_json_list(response_text)
        except Exception:
            recruiter_profiles = []

    if not recruiter_profiles:
        for r in results:
            title = r.get("title", "")
            title_lower = title.lower()
            if any(term in title_lower for term in ["hiring", "jobs", "careers", "recruitment", "scam", "news"]):
                continue
            name = title.split("-")[0].split("|")[0].strip()
            parts = name.split()
            if 2 <= len(parts) <= 4:
                recruiter_profiles.append({"name": name, "linkedin": r.get("url")})

    leads: list[dict[str, Any]] = []
    for profile in recruiter_profiles:
        name = (profile.get("name") or "").strip()
        linkedin = (profile.get("linkedin") or "").strip()
        if not name:
            continue
        parts = name.split()
        cleaned_parts = []
        for p in parts:
            clean_part = re.sub(r"[^a-zA-Z-]", "", p)
            if clean_part and clean_part.upper() not in {
                "MS", "MBA", "PHD", "HR", "RECRUITER", "II", "III", "IV", "V"
            }:
                cleaned_parts.append(clean_part)

        if len(cleaned_parts) >= 2:
            email = f"{cleaned_parts[0].lower()}.{cleaned_parts[-1].lower()}@{domain}"
        else:
            simple_parts = [re.sub(r"[^a-zA-Z-]", "", p) for p in parts if re.sub(r"[^a-zA-Z-]", "", p)]
            if len(simple_parts) >= 2:
                email = f"{simple_parts[0].lower()}.{simple_parts[-1].lower()}@{domain}"
            elif simple_parts:
                email = f"{simple_parts[0].lower()}@{domain}"
            else:
                email = f"recruiter@{domain}"

        status = "guessed"
        if hunter:
            try:
                verify_res = hunter.email_verifier(email)
                if verify_res.get("result") == "deliverable":
                    status = "verified"
            except Exception:
                status = "unverified_limit"

        leads.append({"name": name, "email": email, "linkedin": linkedin, "status": status})

    if not leads and hunter:
        for prefix in ["careers", "hr", "recruiting", "jobs", "talent"]:
            email = f"{prefix}@{domain}"
            try:
                verify_res = hunter.email_verifier(email)
                if verify_res.get("result") == "deliverable":
                    leads.append(
                        {
                            "name": f"{company} HR Team",
                            "email": email,
                            "linkedin": f"https://www.{domain}",
                            "status": "verified",
                        }
                    )
                    break
            except Exception:
                continue

    return leads


def generate_email_body(
    *,
    sender_name: str,
    expertise: str,
    lead_name: str,
    company: str,
    role: str,
) -> str:
    settings = get_settings()
    groq_key = settings.groq_api_key or os.getenv("GROQ_API_KEY")
    first = lead_name.split()[0] if lead_name else "there"
    fallback = (
        f"Hi {first},\n\n"
        f"I'm {sender_name}, interested in the {role} role at {company}. "
        f"My background includes {expertise}. I'd love to connect about this opportunity.\n\n"
        f"Best regards,\n{sender_name}"
    )
    if not groq_key:
        return fallback
    try:
        from langchain_groq import ChatGroq

        llm = ChatGroq(model="llama-3.1-8b-instant", groq_api_key=groq_key, temperature=0.2)
        prompt = (
            f"Write a 3-sentence email from {sender_name} ({expertise}) to {first} "
            f"for {role} at {company}. Format: Hi [Name], ... Best regards, {sender_name}."
        )
        return llm.invoke(prompt).content.strip()
    except Exception:
        return fallback


def execute_cold_email(
    creds: dict[str, Any],
    sender: str,
    to_email: str,
    to_name: str,
    subject: str,
    body: str,
    company: str,
    role: str,
    file_path: str | None,
    send_now: bool,
) -> dict[str, Any]:
    service = get_gmail_service(creds)
    msg = MIMEMultipart()
    msg["to"] = to_email
    msg["subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    new_name = None
    if file_path and os.path.exists(file_path):
        new_name = f"{sender.replace(' ', '_')}_{company.replace(' ', '')}.pdf"
        shutil.copy2(file_path, new_name)
        with open(new_name, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="{new_name}"')
        msg.attach(part)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    if send_now:
        res = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    else:
        res = service.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()

    if new_name and os.path.exists(new_name):
        os.remove(new_name)
    return res
