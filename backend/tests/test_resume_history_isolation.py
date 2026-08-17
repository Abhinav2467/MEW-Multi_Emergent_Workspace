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


@pytest.mark.asyncio
async def test_unauthenticated_user_isolation():
    """Verify that unauthenticated optional user dependency returns guest user (id=1)."""
    from backend.api.deps import get_current_user_optional

    async with aiosqlite.connect(":memory:") as conn:
        conn.row_factory = aiosqlite.Row
        await run_migrations(conn)

        user_repo = UserRepository(conn)
        # Create user 2 with token
        await user_repo.upsert_google_user(
            google_id="google_u2", email="u2@example.com", name="User Two", gmail_tokens_json="{}"
        )

        # Call get_current_user_optional without credentials
        current_user = await get_current_user_optional(credentials=None, conn=conn)

        # Must return Guest Candidate (id=-1), NOT user 2 (id=2)
        assert current_user["id"] == -1
        assert current_user["email"] == "candidate@mew.ai"


@pytest.mark.asyncio
async def test_e2e_resume_upload_and_history_isolation(tmp_path):
    """E2E test: Uploading resume via API persists to DB and isolates history per user."""
    import fitz
    from fastapi.testclient import TestClient
    from backend.main import create_app
    from backend.auth.jwt import create_access_token
    from backend.storage.database import get_db

    # Create dummy PDF
    pdf_path = tmp_path / "Jane_Doe_Resume.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (72, 72),
        "Jane Doe\njane@example.com\n+1 555 0100\nSkills: Python FastAPI\nExperience\n- Engineer",
    )
    doc.save(pdf_path)
    doc.close()

    async with aiosqlite.connect(":memory:") as conn:
        conn.row_factory = aiosqlite.Row
        await run_migrations(conn)

        user_repo = UserRepository(conn)
        u1 = await user_repo.upsert_google_user(
            google_id="u1_g", email="user1@example.com", name="User 1"
        )
        u2 = await user_repo.upsert_google_user(
            google_id="u2_g", email="user2@example.com", name="User 2"
        )

        app = create_app()

        async def override_get_db():
            yield conn

        app.dependency_overrides[get_db] = override_get_db
        client = TestClient(app)

        t1 = create_access_token(user_id=u1["id"], email=u1["email"])
        t2 = create_access_token(user_id=u2["id"], email=u2["email"])

        # 1. User 1 uploads resume
        with open(pdf_path, "rb") as f:
            res_up = client.post(
                "/upload-resume",
                headers={"Authorization": f"Bearer {t1}"},
                files={"file": ("Jane_Doe_Resume.pdf", f, "application/pdf")},
            )
        assert res_up.status_code == 200, res_up.text

        # 2. User 1 history has 1 resume
        res_h1 = client.get("/api/v1/resume/history", headers={"Authorization": f"Bearer {t1}"})
        assert res_h1.status_code == 200
        data1 = res_h1.json()["data"]
        assert len(data1) == 1
        assert data1[0]["filename"] == "Jane_Doe_Resume.pdf"

        # 3. User 2 history is EMPTY (0 resumes)
        res_h2 = client.get("/api/v1/resume/history", headers={"Authorization": f"Bearer {t2}"})
        assert res_h2.status_code == 200
        data2 = res_h2.json()["data"]
        assert len(data2) == 0

        # 4. Unauthenticated guest history should be blocked with 401
        res_guest = client.get("/api/v1/resume/history")
        assert res_guest.status_code == 401


