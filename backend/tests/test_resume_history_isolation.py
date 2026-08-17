"""Tests for multi-tenant data isolation in resume history and user repositories."""

import pytest
import aiosqlite

from backend.storage.migrations import run_migrations
from backend.storage.repositories import ResumeHistoryRepository, AppliedJobRepository, UserRepository


@pytest.mark.asyncio
async def test_resume_history_multi_tenant_isolation():
    """Verify that user history requests return strictly their own resumes."""
    async with aiosqlite.connect(":memory:") as conn:
        conn.row_factory = aiosqlite.Row
        await run_migrations(conn)

        user_repo = UserRepository(conn)
        user1 = await user_repo.upsert_google_user(
            google_id="google_user_1", email="user1@example.com", name="User One"
        )
        user2 = await user_repo.upsert_google_user(
            google_id="google_user_2", email="user2@example.com", name="User Two"
        )

        hist_repo = ResumeHistoryRepository(conn)

        # Guest User 1 uploads resumes (e.g. Videsh_Resume and Joshith_Resume uploaded in guest mode or user 1)
        await hist_repo.record_resume(user_id=1, filename="Videsh_Resume.pdf", file_size_bytes=100000)
        await hist_repo.record_resume(user_id=1, filename="Joshith_Resume.pdf", file_size_bytes=600000)

        # User 2 (a newly registered/distinct user) has NOT uploaded any resume yet.
        user2_history = await hist_repo.list_for_user(user2["id"])

        # User 2 history MUST be empty and MUST NOT contain User 1's resumes
        assert len(user2_history) == 0, f"User 2 received leaked resumes: {user2_history}"

        # User 1 history MUST contain exactly 2 resumes
        user1_history = await hist_repo.list_for_user(1)
        assert len(user1_history) == 2
        assert user1_history[0]["filename"] == "Joshith_Resume.pdf"
        assert user1_history[1]["filename"] == "Videsh_Resume.pdf"

        # Now User 2 uploads their own resume
        await hist_repo.record_resume(user_id=user2["id"], filename="User2_Resume.pdf", file_size_bytes=200000)

        # User 2 history should only contain User 2's resume
        user2_updated_history = await hist_repo.list_for_user(user2["id"])
        assert len(user2_updated_history) == 1
        assert user2_updated_history[0]["filename"] == "User2_Resume.pdf"


@pytest.mark.asyncio
async def test_applied_jobs_multi_tenant_isolation():
    """Verify that applied jobs queries strictly isolate records by user_id."""
    async with aiosqlite.connect(":memory:") as conn:
        conn.row_factory = aiosqlite.Row
        await run_migrations(conn)

        user_repo = UserRepository(conn)
        user1 = await user_repo.upsert_google_user(
            google_id="google_u1", email="u1@example.com", name="User One"
        )
        user2 = await user_repo.upsert_google_user(
            google_id="google_u2", email="u2@example.com", name="User Two"
        )

        applied_repo = AppliedJobRepository(conn)

        # Record applied job for Guest User 1
        await applied_repo.record_application(
            user_id=1,
            company_name="Acme Corp",
            position="AI Engineer",
            apply_link="https://acme.com/jobs/1",
        )

        # User 2 listing should be empty
        user2_jobs = await applied_repo.list_for_user(user2["id"])
        assert len(user2_jobs) == 0, f"User 2 received leaked applied jobs: {user2_jobs}"

        # User 1 listing should have 1 item
        user1_jobs = await applied_repo.list_for_user(1)
        assert len(user1_jobs) == 1
        assert user1_jobs[0]["company_name"] == "Acme Corp"
