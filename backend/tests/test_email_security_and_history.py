"""Unit tests for duplicate email security enforcement and user-scoped resume history isolation."""

import pytest
import aiosqlite
from fastapi.testclient import TestClient

from backend.main import app
from backend.storage.database import get_db
from backend.storage.migrations import run_migrations
from backend.storage.repositories import (
    UserRepository,
    ResumeHistoryRepository,
    AppliedJobRepository,
)
from backend.auth.jwt import create_access_token


@pytest.mark.asyncio
async def test_resume_history_strict_user_isolation():
    """Verify that resume history is strictly isolated per user account and never leaks user 1's history."""
    async with aiosqlite.connect(":memory:") as conn:
        conn.row_factory = aiosqlite.Row
        await run_migrations(conn)

        user_repo = UserRepository(conn)
        user1 = await user_repo.upsert_google_user(
            google_id="google_u1", email="user1@mew.ai", name="User One"
        )
        user2 = await user_repo.upsert_google_user(
            google_id="google_u2", email="user2@mew.ai", name="User Two"
        )

        hist_repo = ResumeHistoryRepository(conn)
        await hist_repo.record_resume(
            user_id=user1["id"], filename="User1_CV.pdf", file_size_bytes=1024
        )
        await hist_repo.record_resume(
            user_id=user2["id"], filename="User2_CV.pdf", file_size_bytes=2048
        )

        # Retrieve for User 2
        u2_history = await hist_repo.list_for_user(user2["id"])
        assert len(u2_history) == 1
        assert u2_history[0]["filename"] == "User2_CV.pdf"
        assert u2_history[0]["user_id"] == user2["id"]

        # Retrieve for User 1
        u1_history = await hist_repo.list_for_user(user1["id"])
        assert len(u1_history) == 1
        assert u1_history[0]["filename"] == "User1_CV.pdf"


@pytest.mark.asyncio
async def test_applied_jobs_strict_user_isolation():
    """Verify that applied jobs are strictly isolated per user account."""
    async with aiosqlite.connect(":memory:") as conn:
        conn.row_factory = aiosqlite.Row
        await run_migrations(conn)

        user_repo = UserRepository(conn)
        user1 = await user_repo.upsert_google_user(
            google_id="google_u1", email="user1@mew.ai", name="User One"
        )
        user2 = await user_repo.upsert_google_user(
            google_id="google_u2", email="user2@mew.ai", name="User Two"
        )

        app_repo = AppliedJobRepository(conn)
        await app_repo.record_application(
            user_id=user1["id"],
            company_name="Google",
            position="AI Engineer",
            apply_link="https://google.com/apply",
        )
        await app_repo.record_application(
            user_id=user2["id"],
            company_name="Meta",
            position="Backend Engineer",
            apply_link="https://meta.com/apply",
        )

        u2_apps = await app_repo.list_for_user(user2["id"])
        assert len(u2_apps) == 1
        assert u2_apps[0]["company_name"] == "Meta"


@pytest.mark.asyncio
async def test_duplicate_email_prevention_on_profile_update():
    """Verify that editing profile email to another registered user's email is rejected with exact error detail."""
    async with aiosqlite.connect(":memory:") as conn:
        conn.row_factory = aiosqlite.Row
        await run_migrations(conn)

        user_repo = UserRepository(conn)
        user1 = await user_repo.upsert_google_user(
            google_id="google_u1", email="email1@mew.ai", name="First User"
        )
        user2 = await user_repo.upsert_google_user(
            google_id="google_u2", email="email2@mew.ai", name="Second User"
        )

        async def override_get_db():
            yield conn

        app.dependency_overrides[get_db] = override_get_db
        try:
            token_u1 = create_access_token(user_id=user1["id"], email=user1["email"])
            client = TestClient(app)

            # User 1 attempts editing email to email2@mew.ai (User 2's email)
            resp = client.put(
                "/api/v1/profile",
                json={"email": "email2@mew.ai", "name": "First User"},
                headers={"Authorization": f"Bearer {token_u1}"},
            )

            assert resp.status_code == 400
            err_detail = resp.json()["detail"]
            assert err_detail == "You can't use this email. It's registered with another user, and you can't use it."
        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_unregistered_email_update_flags_google_reauth():
    """Verify that editing profile email to an unregistered email flags Google re-authentication requirement."""
    async with aiosqlite.connect(":memory:") as conn:
        conn.row_factory = aiosqlite.Row
        await run_migrations(conn)

        user_repo = UserRepository(conn)
        user1 = await user_repo.upsert_google_user(
            google_id="google_u1", email="email1@mew.ai", name="First User"
        )

        async def override_get_db():
            yield conn

        app.dependency_overrides[get_db] = override_get_db
        try:
            token_u1 = create_access_token(user_id=user1["id"], email=user1["email"])
            client = TestClient(app)

            # User 1 updates email to a brand new email
            resp = client.put(
                "/api/v1/profile",
                json={"email": "new_brand_email@mew.ai", "name": "First User"},
                headers={"Authorization": f"Bearer {token_u1}"},
            )

            assert resp.status_code == 200
            res_json = resp.json()
            assert res_json["status"] == "success"
            assert res_json.get("requires_google_reauth") is True
        finally:
            app.dependency_overrides.clear()
