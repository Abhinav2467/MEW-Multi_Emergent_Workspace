"""Unit tests for Gemini key resolution, job dedupe, and link checker."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from backend.agents.job_search.link_checker import filter_alive_apply_links
from backend.agents.job_search.matcher import (
    dedupe_jobs,
    normalize_apply_url,
    normalize_job_identity,
    score_jobs,
)
from backend.config import Settings, get_settings
from backend.models.schemas import ContactInfo, ParsedProfile


def test_resolved_gemini_api_key_prefers_gemini():
    s = Settings(gemini_api_key="gemini-key", google_api_key="google-key")
    assert s.resolved_gemini_api_key == "gemini-key"


def test_resolved_gemini_api_key_falls_back_to_google():
    s = Settings(gemini_api_key="", google_api_key="google-only")
    assert s.resolved_gemini_api_key == "google-only"


def test_normalize_apply_url_strips_tracking():
    url = "https://WWW.Example.com/jobs/1/?utm_source=li&ref=board&id=9"
    assert normalize_apply_url(url) == "https://example.com/jobs/1?id=9"


def test_normalize_job_identity():
    assert normalize_job_identity("Acme, Inc.", "Software Engineer!") == (
        "acme inc|software engineer"
    )


def test_dedupe_by_url_and_company_title():
    jobs = [
        {
            "company_name": "Acme",
            "position": "SWE Intern",
            "apply_link": "https://boards.greenhouse.io/acme/jobs/1?utm_source=x",
            "matching_percentage": 50,
            "relevant_skills": "Python",
            "_score": 10,
        },
        {
            "company_name": "Acme",
            "position": "SWE Intern",
            "apply_link": "https://acme.com/careers/swe-intern",
            "matching_percentage": 80,
            "relevant_skills": "React",
            "_score": 30,
        },
        {
            "company_name": "Acme",
            "position": "SWE Intern",
            "apply_link": "https://boards.greenhouse.io/acme/jobs/1",
            "matching_percentage": 60,
            "relevant_skills": "FastAPI",
            "_score": 20,
        },
        {
            "company_name": "OtherCo",
            "position": "Backend Eng",
            "apply_link": "https://other.com/jobs/2",
            "matching_percentage": 40,
            "relevant_skills": "SQL",
            "_score": 5,
        },
    ]
    out = dedupe_jobs(jobs)
    assert len(out) == 2
    acme = next(j for j in out if j["company_name"] == "Acme")
    assert acme["matching_percentage"] == 80
    assert "Python" in acme["relevant_skills"] or "React" in acme["relevant_skills"]


def test_score_jobs_dedupes_before_top_n():
    profile = ParsedProfile(
        contact=ContactInfo(name="Test"),
        skills=["Python", "FastAPI"],
        raw_text="python fastapi engineer",
    )
    jobs = [
        {
            "title": "Junior Backend Engineer",
            "description": "python fastapi",
            "company": {"name": "Acme"},
            "url": "https://a.com/1?utm_source=x",
            "job_type": "FULL_TIME",
            "experience_low_level": 0,
            "experience_high_level": 2,
            "location": "Remote",
        },
        {
            "title": "Junior Backend Engineer",
            "description": "python fastapi",
            "company": {"name": "Acme"},
            "url": "https://b.com/2",
            "job_type": "FULL_TIME",
            "experience_low_level": 0,
            "experience_high_level": 2,
            "location": "Remote",
        },
    ]
    matches = score_jobs(jobs, profile, top_n=5)
    assert len(matches) == 1
    assert matches[0]["company_name"] == "Acme"


@pytest.mark.asyncio
async def test_filter_alive_apply_links():
    jobs = [
        {"apply_link": "https://good.example/job", "company_name": "Good"},
        {"apply_link": "https://bad.example/job", "company_name": "Bad"},
        {"apply_link": "not-a-url", "company_name": "Invalid"},
    ]

    class FakeResp:
        def __init__(self, status_code: int) -> None:
            self.status_code = status_code

    async def fake_head(url: str, *args, **kwargs):
        if "good" in url:
            return FakeResp(200)
        return FakeResp(404)

    async def fake_get(url: str, *args, **kwargs):
        return FakeResp(404)

    mock_client = MagicMock()
    mock_client.head = AsyncMock(side_effect=fake_head)
    mock_client.get = AsyncMock(side_effect=fake_get)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("backend.agents.job_search.link_checker.httpx.AsyncClient", return_value=mock_client):
        alive = await filter_alive_apply_links(jobs, concurrency=2, timeout=1.0)

    assert len(alive) == 1
    assert alive[0]["company_name"] == "Good"


def test_get_settings_cache_has_resolved_key_property():
    get_settings.cache_clear()
    # Just ensure property exists on loaded settings class
    assert hasattr(Settings(), "resolved_gemini_api_key")
