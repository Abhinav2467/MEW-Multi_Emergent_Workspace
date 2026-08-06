"""Basic unit tests for matcher and JWT."""

from __future__ import annotations

from backend.auth.jwt import create_access_token, decode_access_token
from backend.agents.job_search.matcher import score_jobs
from backend.models.schemas import ContactInfo, ParsedProfile


def test_jwt_roundtrip():
    token = create_access_token(user_id=42, email="a@b.com")
    payload = decode_access_token(token)
    assert payload["sub"] == "42"
    assert payload["email"] == "a@b.com"


def test_score_jobs_prefers_matching_skills():
    profile = ParsedProfile(
        contact=ContactInfo(name="Test User"),
        skills=["Python", "FastAPI", "React"],
        raw_text="experienced with python fastapi and react",
    )
    jobs = [
        {
            "title": "Junior Backend Engineer",
            "description": "Build APIs with python and fastapi",
            "company": {"name": "Acme"},
            "url": "https://acme.com/jobs/1",
            "job_type": "FULL_TIME",
            "experience_low_level": 0,
            "experience_high_level": 2,
            "location": "Remote",
        },
        {
            "title": "Senior Principal Architect",
            "description": "python fastapi",
            "company": {"name": "SkipCo"},
            "url": "https://skip.co/1",
            "job_type": "FULL_TIME",
            "experience_low_level": 0,
            "experience_high_level": 2,
            "location": "Remote",
        },
    ]
    matches = score_jobs(jobs, profile, top_n=5)
    assert len(matches) == 1
    assert matches[0]["company_name"] == "Acme"
    assert matches[0]["matching_percentage"] > 0
    assert "Python" in matches[0]["relevant_skills"] or "Fastapi" in matches[0]["relevant_skills"]
