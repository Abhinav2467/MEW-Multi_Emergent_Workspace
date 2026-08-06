"""Test suite verifying active profile sync to profile.json and autofill matching."""

import json
import pytest
import aiosqlite
from pathlib import Path
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.models.schemas import ContactInfo, ParsedProfile
from backend.storage.migrations import run_migrations
from backend.storage.profile_sync import PROFILE_JSON_PATH, sync_profile_to_autofill_json
from backend.storage.repositories import ProfileRepository, UserRepository


@pytest.mark.asyncio
async def test_sync_profile_to_autofill_json_updates_file(tmp_path, monkeypatch):
    test_json_path = tmp_path / "data" / "profile.json"
    monkeypatch.setattr("backend.storage.profile_sync.PROFILE_JSON_PATH", test_json_path)

    profile = ParsedProfile(
        contact=ContactInfo(
            name="KP Videsh Kumaar",
            email="videshkumaar@example.com",
            phone="+91-9876543210",
            linkedin="https://linkedin.com/in/videshkumaar",
            links=["https://github.com/videshkumaar"],
        ),
        skills=["Python", "FastAPI", "Machine Learning"],
        experience_years=4.5,
        current_role="AI Engineer",
        raw_text="AI Engineer with experience in Python and FastAPI.",
    )

    synced_data = sync_profile_to_autofill_json(profile, resume_file_path="/path/to/videsh_resume.pdf")

    assert test_json_path.exists()
    with open(test_json_path, "r", encoding="utf-8") as f:
        file_content = json.load(f)

    assert file_content["personal"]["first_name"] == "KP"
    assert file_content["personal"]["last_name"] == "Videsh Kumaar"
    assert file_content["personal"]["full_name"] == "KP Videsh Kumaar"
    assert file_content["personal"]["email"] == "videshkumaar@example.com"
    assert file_content["personal"]["phone"] == "+91-9876543210"
    assert file_content["professional"]["current_title"] == "AI Engineer"
    assert "Python" in file_content["professional"]["primary_skills"]
    assert file_content["resume_file_path"] == "/path/to/videsh_resume.pdf"


@pytest.mark.asyncio
async def test_autofill_payload_reflects_new_user_resume_upload(tmp_path, monkeypatch):
    test_json_path = tmp_path / "data" / "profile.json"
    monkeypatch.setattr("backend.storage.profile_sync.PROFILE_JSON_PATH", test_json_path)

    async with aiosqlite.connect(":memory:") as conn:
        conn.row_factory = aiosqlite.Row
        await run_migrations(conn)

        user_repo = UserRepository(conn)
        user = await user_repo.upsert_google_user(
            google_id="google_videsh_789",
            email="videshkumaar@example.com",
            name="KP Videsh Kumaar",
        )

        prof_repo = ProfileRepository(conn)
        profile_data = ParsedProfile(
            contact=ContactInfo(
                name="KP Videsh Kumaar",
                email="videshkumaar@example.com",
                phone="+91-9876543210",
                linkedin="https://linkedin.com/in/videshkumaar",
            ),
            skills=["Python", "Deep Learning"],
            experience_years=4.0,
            current_role="Lead AI Specialist",
        )
        record = await prof_repo.create(
            user_id=user["id"],
            profile=profile_data,
            parse_method="gemini",
            resume_file_path="/tmp/videsh_resume.pdf",
        )
        sync_profile_to_autofill_json(profile_data, resume_file_path="/tmp/videsh_resume.pdf")

        app = create_app()

        async def override_get_db():
            yield conn

        from backend.storage.database import get_db
        app.dependency_overrides[get_db] = override_get_db

        client = TestClient(app)

        # 1. Preview payload check
        res_preview = client.get(f"/autofill/preview?user_id={user['id']}")
        assert res_preview.status_code == 200
        preview_data = res_preview.json()["data"]["active_profile"]
        assert preview_data["personal"]["full_name"] == "KP Videsh Kumaar"
        assert preview_data["personal"]["email"] == "videshkumaar@example.com"

        # 2. Form field matching check
        fields = [
            {"element_id": "name_field", "label": "Full Name", "placeholder": "Enter name", "tag_name": "input", "input_type": "text"},
            {"element_id": "email_field", "label": "Email Address", "placeholder": "Email", "tag_name": "input", "input_type": "email"},
            {"element_id": "phone_field", "label": "Phone Number", "placeholder": "Phone", "tag_name": "input", "input_type": "tel"},
        ]

        res_match = client.post(f"/api/v1/autofill-payload/match?user_id={user['id']}", json={"fields": fields})
        assert res_match.status_code == 200
        matches = res_match.json()["data"]["matches"]
        assert len(matches) >= 2

        name_match = next(m for m in matches if m["element_id"] == "name_field")
        assert name_match["value"] == "KP Videsh Kumaar"

        email_match = next(m for m in matches if m["element_id"] == "email_field")
        assert email_match["value"] == "videshkumaar@example.com"
