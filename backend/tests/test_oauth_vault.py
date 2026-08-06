"""Unit tests verifying persistent Google OAuth refresh token vault."""

import pytest
import aiosqlite

from backend.storage.migrations import run_migrations
from backend.storage.repositories import UserRepository
from backend.auth.google_oauth import build_auth_url


@pytest.mark.asyncio
async def test_build_auth_url_contains_offline_access():
    url = build_auth_url()
    assert "access_type=offline" in url
    assert "prompt=consent" in url


@pytest.mark.asyncio
async def test_google_refresh_token_persistence():
    async with aiosqlite.connect(":memory:") as conn:
        conn.row_factory = aiosqlite.Row
        await run_migrations(conn)

        user_repo = UserRepository(conn)
        user = await user_repo.upsert_google_user(
            google_id="google_vault_123",
            email="researcher@example.com",
            name="Research Candidate",
            google_refresh_token="mock_persistent_refresh_token_xyz",
        )

        assert user["google_refresh_token"] == "mock_persistent_refresh_token_xyz"

        # Verify retrieval by google_id
        retrieved = await user_repo.get_by_google_id("google_vault_123")
        assert retrieved is not None
        assert retrieved["google_refresh_token"] == "mock_persistent_refresh_token_xyz"

        # Verify update_google_refresh_token
        await user_repo.update_google_refresh_token(user["id"], "updated_token_999")
        updated = await user_repo.get_by_id(user["id"])
        assert updated["google_refresh_token"] == "updated_token_999"
