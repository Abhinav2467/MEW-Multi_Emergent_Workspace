"""Job matching against CareerZenith postings using profile skills."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from backend.agents.job_search.careerzenith import parse_job_created_at
from backend.models.schemas import ParsedProfile

CONTEXT_KEYWORDS = [
    "full-stack",
    "backend",
    "frontend",
    "ai",
    "machine learning",
    "database engine",
    "search engine",
    "recommendation",
    "parser",
    "network security",
    "automation",
    "chatgpt",
]

BASE_SKILLS = [
    "react", "node", "express", "next", "fastapi", "tailwind", "redux", "docker", "git",
    "python", "c++", "c", "java", "javascript", "typescript",
    "mongodb", "sql", "vector database", "pinecone",
    "rag", "llama", "gemini", "genkit", "agentic", "langchain", "langgraph",
    "packet inspection", "wireshark", "multi-thread", "concurrency", "rest api",
    "distributed systems", "css", "html", "mysql", "oop",
]

TRACKING_QUERY_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "ref",
    "source",
    "fbclid",
    "gclid",
}


def _skill_vocab(profile: ParsedProfile) -> list[str]:
    profile_skills = [s.lower().strip() for s in profile.skills if s.strip()]
    combined = list(dict.fromkeys(profile_skills + BASE_SKILLS))
    return combined


def normalize_apply_url(url: str) -> str:
    """Normalize apply URLs for duplicate detection."""
    if not url:
        return ""
    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = (parsed.path or "").rstrip("/")
    query_pairs = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if k.lower() not in TRACKING_QUERY_PARAMS and not k.lower().startswith("utm_")
    ]
    query = urlencode(sorted(query_pairs))
    return urlunparse(("https" if parsed.scheme else "", host, path, "", query, ""))


def normalize_job_identity(company: str, title: str) -> str:
    """Content key: company + title, lowercased and stripped of punctuation."""
    def _clean(value: str) -> str:
        value = (value or "").lower()
        value = re.sub(r"[^\w\s]", " ", value)
        value = re.sub(r"\s+", " ", value).strip()
        return value

    return f"{_clean(company)}|{_clean(title)}"


def _merge_skills(a: str, b: str) -> str:
    skills = set()
    for blob in (a, b):
        for part in (blob or "").split(","):
            s = part.strip()
            if s:
                skills.add(s)
    return ", ".join(sorted(skills))


def _rank_tuple(job: dict[str, Any]) -> tuple[int, int, float]:
    created = parse_job_created_at(job.get("created_at"))
    ts = created.timestamp() if created else 0.0
    return (
        int(job.get("matching_percentage") or 0),
        int(job.get("_score") or 0),
        ts,
    )


def _sort_by_posted_at(jobs: list[dict[str, Any]], *, reverse: bool = True) -> list[dict[str, Any]]:
    """Sort jobs by listing timestamp (newest first by default)."""
    return sorted(
        jobs,
        key=lambda j: parse_job_created_at(j.get("created_at"))
        or datetime.min.replace(tzinfo=UTC),
        reverse=reverse,
    )


def dedupe_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse duplicate openings by URL and by company+title."""
    by_url: dict[str, dict[str, Any]] = {}
    for job in jobs:
        url_key = normalize_apply_url(job.get("apply_link") or "")
        if not url_key:
            # Keep unique empty-url rows under a synthetic key
            url_key = f"__no_url__{id(job)}"
        existing = by_url.get(url_key)
        if existing is None or _rank_tuple(job) > _rank_tuple(existing):
            if existing is not None:
                job = {
                    **job,
                    "relevant_skills": _merge_skills(
                        existing.get("relevant_skills", ""),
                        job.get("relevant_skills", ""),
                    ),
                }
            by_url[url_key] = job
        else:
            existing["relevant_skills"] = _merge_skills(
                existing.get("relevant_skills", ""),
                job.get("relevant_skills", ""),
            )

    by_identity: dict[str, dict[str, Any]] = {}
    for job in by_url.values():
        identity = normalize_job_identity(
            job.get("company_name") or "",
            job.get("position") or "",
        )
        if not identity or identity == "|":
            identity = f"__anon__{id(job)}"
        existing = by_identity.get(identity)
        if existing is None or _rank_tuple(job) > _rank_tuple(existing):
            if existing is not None:
                job = {
                    **job,
                    "relevant_skills": _merge_skills(
                        existing.get("relevant_skills", ""),
                        job.get("relevant_skills", ""),
                    ),
                }
            by_identity[identity] = job
        else:
            existing["relevant_skills"] = _merge_skills(
                existing.get("relevant_skills", ""),
                job.get("relevant_skills", ""),
            )

    deduped = list(by_identity.values())
    deduped.sort(key=_rank_tuple, reverse=True)
    return deduped


def score_jobs(
    jobs: list[dict[str, Any]],
    profile: ParsedProfile,
    top_n: int = 15,
    *,
    dedupe: bool = True,
    strip_internal: bool = True,
) -> list[dict[str, Any]]:
    skills_dict = _skill_vocab(profile)
    candidate_skills = [s.lower() for s in profile.skills]
    resume_text_lower = (profile.raw_text or "").lower()

    scored: list[dict[str, Any]] = []
    for job in jobs:
        title = (job.get("title") or "").strip()
        desc = (job.get("description") or "").strip()
        company = (job.get("company") or {}).get("name", "").strip()
        url = (job.get("url") or "").strip()
        job_type = (job.get("job_type") or "").strip()
        exp_low = int(job.get("experience_low_level") or 0)
        exp_high = int(job.get("experience_high_level") or 0)

        title_lower = title.lower()
        desc_lower = desc.lower()

        if (exp_low > 6 or any(k in title_lower for k in ["senior principal", "principal architect"])) and job_type != "INTERNSHIP":
            continue

        matched_skills: list[str] = []
        for skill in skills_dict:
            pattern = rf"\b{re.escape(skill)}\b"
            if re.search(pattern, desc_lower) or re.search(pattern, title_lower):
                matched_skills.append(skill)

        score = len(matched_skills) * 10
        for kw in CONTEXT_KEYWORDS:
            pattern = rf"\b{re.escape(kw)}\b"
            if re.search(pattern, desc_lower) or re.search(pattern, title_lower):
                score += 3

        if job_type == "INTERNSHIP" or any(k in title_lower for k in ["intern", "trainee", "graduate"]):
            score += 15

        matched_in_resume: list[str] = []
        for skill in matched_skills:
            if skill in candidate_skills or re.search(rf"\b{re.escape(skill)}\b", resume_text_lower):
                matched_in_resume.append(skill)

        if not matched_in_resume and any(k in title_lower for k in ["software", "developer", "engineer", "scientist", "analyst"]):
            matched_in_resume = candidate_skills[:2] if len(candidate_skills) >= 2 else ["python", "react"]

        if not matched_in_resume:
            continue

        base_count = max(len(candidate_skills), 1)
        match_percentage = min(int((len(matched_in_resume) / base_count) * 100) + 45, 100)
        if any(k in title_lower for k in ["full stack", "backend", "cloud", "scientist", "lead"]):
            match_percentage = min(match_percentage + 15, 100)

        scored.append(
            {
                "company_name": company,
                "position": title,
                "apply_link": url,
                "job_type": job_type,
                "location": job.get("location", ""),
                "experience": f"{exp_low}-{exp_high} years",
                "matching_percentage": match_percentage,
                "relevant_skills": ", ".join(sorted(set(s.title() for s in matched_in_resume))),
                "hr_recruiter_name": None,
                "hr_recruiter_email": None,
                "created_at": job.get("created_at"),
                "description": desc,
                "clean_description": re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', desc)).strip() if desc else "",
                "_score": score,
            }
        )

    if dedupe:
        scored = dedupe_jobs(scored)

    # Rank by relevance (matching_percentage) first (descending), then by timestamp (newest first)
    scored.sort(key=_rank_tuple, reverse=True)

    top = scored[:top_n]
    if strip_internal:
        for item in top:
            item.pop("_score", None)
    return top
