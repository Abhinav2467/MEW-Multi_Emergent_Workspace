"""Tests for job recency filter and posted-at sorting."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from backend.agents.job_search.careerzenith import (
    filter_jobs_within_days,
    parse_job_created_at,
)
from backend.agents.job_search.matcher import score_jobs
from backend.models.schemas import ContactInfo, ParsedProfile


def test_parse_job_created_at_iso_z():
    dt = parse_job_created_at("2026-07-20T10:00:00Z")
    assert dt is not None
    assert dt.year == 2026
    assert dt.month == 7


def test_filter_jobs_within_days():
    now = datetime.now(UTC)
    recent = (now - timedelta(days=5)).isoformat().replace("+00:00", "Z")
    old = (now - timedelta(days=30)).isoformat().replace("+00:00", "Z")
    jobs = [
        {"title": "New", "created_at": recent},
        {"title": "Old", "created_at": old},
        {"title": "NoDate"},
    ]
    out = filter_jobs_within_days(jobs, days=15)
    assert len(out) == 1
    assert out[0]["title"] == "New"


def test_score_jobs_sorted_by_posted_at_newest_first():
    now = datetime.now(UTC)
    older = (now - timedelta(days=10)).isoformat().replace("+00:00", "Z")
    newer = (now - timedelta(days=2)).isoformat().replace("+00:00", "Z")
    profile = ParsedProfile(
        contact=ContactInfo(name="Test"),
        skills=["Python"],
        raw_text="python developer",
    )
    jobs = [
        {
            "title": "Junior Engineer",
            "description": "python",
            "company": {"name": "OlderCo"},
            "url": "https://older.com/1",
            "job_type": "FULL_TIME",
            "experience_low_level": 0,
            "experience_high_level": 2,
            "location": "Remote",
            "created_at": older,
        },
        {
            "title": "Junior Engineer",
            "description": "python",
            "company": {"name": "NewerCo"},
            "url": "https://newer.com/1",
            "job_type": "FULL_TIME",
            "experience_low_level": 0,
            "experience_high_level": 2,
            "location": "Remote",
            "created_at": newer,
        },
    ]
    matches = score_jobs(jobs, profile, top_n=5, dedupe=False)
    assert len(matches) == 2
    assert matches[0]["company_name"] == "NewerCo"
    assert matches[1]["company_name"] == "OlderCo"


import pytest
import aiosqlite
from backend.storage.migrations import run_migrations
from backend.storage.repositories import JobMatchRepository, ReportRepository, ProfileRepository


@pytest.mark.asyncio
async def test_job_match_repository_persists_and_sorts_created_at():
    async with aiosqlite.connect(":memory:") as conn:
        conn.row_factory = aiosqlite.Row
        await run_migrations(conn)

        prof_repo = ProfileRepository(conn)
        profile = await prof_repo.create(
            user_id=1,
            profile=ParsedProfile(contact=ContactInfo(name="Test")),
            parse_method="test",
            resume_file_path=None,
        )
        rep_repo = ReportRepository(conn)
        report = await rep_repo.create(user_id=1, profile_id=profile["id"])

        match_repo = JobMatchRepository(conn)
        matches = [
            {
                "company_name": "OlderCo",
                "position": "Dev",
                "apply_link": "https://older.com",
                "matching_percentage": 90,
                "relevant_skills": "Python",
                "created_at": "2026-07-10T10:00:00Z",
            },
            {
                "company_name": "NewerCo",
                "position": "Dev",
                "apply_link": "https://newer.com",
                "matching_percentage": 70,
                "relevant_skills": "Python",
                "created_at": "2026-07-25T10:00:00Z",
            },
        ]
        await match_repo.bulk_create(report["id"], matches)
        listed = await match_repo.list_for_report(report["id"])
        assert len(listed) == 2
        assert listed[0]["company_name"] == "NewerCo"
        assert listed[0]["created_at"] == "2026-07-25T10:00:00Z"

