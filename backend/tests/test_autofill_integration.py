"""Integration tests for Autofill endpoints using SQLite parsed profile storage."""

import pytest
import aiosqlite
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.models.schemas import ContactInfo, ParsedProfile
from backend.storage.migrations import run_migrations
from backend.storage.repositories import ProfileRepository, UserRepository


@pytest.mark.asyncio
async def test_autofill_payload_uses_sqlite_parsed_profile(tmp_path, monkeypatch):
    test_json_path = tmp_path / "data" / "profile.json"
    monkeypatch.setattr("backend.storage.profile_sync.PROFILE_JSON_PATH", test_json_path)

    async with aiosqlite.connect(":memory:") as conn:
        conn.row_factory = aiosqlite.Row
        await run_migrations(conn)

        user_repo = UserRepository(conn)
        user = await user_repo.upsert_google_user(
            google_id="google_123",
            email="testuser@example.com",
            name="John Doe",
        )

        prof_repo = ProfileRepository(conn)
        profile_data = ParsedProfile(
            contact=ContactInfo(
                name="John Doe",
                email="john.doe@example.com",
                phone="+1-555-0199",
                linkedin="https://linkedin.com/in/johndoe",
                links=["https://github.com/johndoe", "https://johndoe.dev"],
            ),
            skills=["Python", "FastAPI", "React"],
            experience_years=5.0,
            current_role="Senior Software Engineer",
            raw_text="Experienced engineer working with Python and FastAPI.",
        )
        await prof_repo.create(
            user_id=user["id"],
            profile=profile_data,
            parse_method="deterministic",
            resume_file_path=None,
        )

        app = create_app()

        async def override_get_db():
            yield conn

        from backend.storage.database import get_db
        app.dependency_overrides[get_db] = override_get_db

        client = TestClient(app)

        res = client.get(f"/api/v1/autofill-payload?user_id={user['id']}")
        assert res.status_code == 200
        data = res.json()["data"]

        assert data["personal"]["first_name"] == "John"
        assert data["personal"]["last_name"] == "Doe"
        assert data["personal"]["email"] == "john.doe@example.com"
        assert data["personal"]["phone"] == "+1-555-0199"
        assert data["personal"]["linkedin_url"] == "https://linkedin.com/in/johndoe"
        assert data["professional"]["current_title"] == "Senior Software Engineer"
        assert "Python" in data["professional"]["primary_skills"]

        dom_fields = [
            {
                "element_id": "fname_input",
                "label": "First Name",
                "placeholder": "Enter first name",
                "tag_name": "input",
                "input_type": "text",
            },
            {
                "element_id": "email_input",
                "label": "Email Address",
                "placeholder": "you@example.com",
                "tag_name": "input",
                "input_type": "email",
            },
        ]
        res_match = client.post(f"/api/v1/autofill-payload/match?user_id={user['id']}", json={"fields": dom_fields})
        assert res_match.status_code == 200
        matches = res_match.json()["data"]["matches"]
        assert len(matches) >= 1

        fname_match = next(m for m in matches if m["element_id"] == "fname_input")
        assert fname_match["value"] == "John"


@pytest.mark.asyncio
async def test_download_latest_resume_file(tmp_path):
    async with aiosqlite.connect(":memory:") as conn:
        conn.row_factory = aiosqlite.Row
        await run_migrations(conn)

        user_repo = UserRepository(conn)
        user = await user_repo.upsert_google_user(
            google_id="google_456",
            email="pdfuser@example.com",
            name="PDF User",
        )

        pdf_file = tmp_path / "sample_resume.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 dummy content")

        prof_repo = ProfileRepository(conn)
        profile_data = ParsedProfile(
            contact=ContactInfo(name="PDF User", email="pdfuser@example.com"),
            skills=["Python"],
            experience_years=3.0,
            current_role="Developer",
        )
        await prof_repo.create(
            user_id=user["id"],
            profile=profile_data,
            parse_method="deterministic",
            resume_file_path=str(pdf_file),
        )

        app = create_app()

        async def override_get_db():
            yield conn

        from backend.storage.database import get_db
        app.dependency_overrides[get_db] = override_get_db

        client = TestClient(app)

        res = client.get("/api/v1/resume/download-latest")
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/pdf"
        assert b"%PDF-1.4" in res.content


@pytest.mark.asyncio
async def test_phone_and_location_autofill_matching(tmp_path, monkeypatch):
    test_json_path = tmp_path / "data" / "profile.json"
    monkeypatch.setattr("backend.storage.profile_sync.PROFILE_JSON_PATH", test_json_path)

    async with aiosqlite.connect(":memory:") as conn:
        conn.row_factory = aiosqlite.Row
        await run_migrations(conn)

        user_repo = UserRepository(conn)
        user = await user_repo.upsert_google_user(
            google_id="google_phone_loc",
            email="candidate@example.com",
            name="Alpha Candidate",
        )

        prof_repo = ProfileRepository(conn)
        profile_data = ParsedProfile(
            contact=ContactInfo(
                name="Alpha Candidate",
                email="candidate@example.com",
                phone="+1-555-9876",
                location="Bengaluru, India",
            ),
            skills=["Python", "FastAPI"],
            experience_years=4.0,
            current_role="Senior Software Developer",
        )
        await prof_repo.create(
            user_id=user["id"],
            profile=profile_data,
            parse_method="deterministic",
            resume_file_path=None,
        )

        app = create_app()

        async def override_get_db():
            yield conn

        from backend.storage.database import get_db
        app.dependency_overrides[get_db] = override_get_db

        client = TestClient(app)

        fields = [
            {"element_id": "phone_input", "label": "Phone Number", "placeholder": "Mobile", "tag_name": "input", "input_type": "tel"},
            {"element_id": "location_input", "label": "Location", "placeholder": "City, Country", "tag_name": "input", "input_type": "text"},
        ]

        res = client.post(f"/api/v1/autofill-payload/match?user_id={user['id']}", json={"fields": fields})
        assert res.status_code == 200
        matches = res.json()["data"]["matches"]
        assert len(matches) >= 2

        phone_match = next(m for m in matches if m["element_id"] == "phone_input")
        assert phone_match["value"] == "+1-555-9876"

        loc_match = next(m for m in matches if m["element_id"] == "location_input")
        assert loc_match["value"] == "Bengaluru, India"

