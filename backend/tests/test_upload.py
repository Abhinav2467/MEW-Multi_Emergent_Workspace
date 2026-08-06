"""API integration smoke tests."""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

from backend.auth.jwt import create_access_token
from backend.main import app
from backend.storage.database import connect
from backend.storage.migrations import run_migrations
from backend.storage.repositories import UserRepository


def _seed_user():
    async def seed():
        c = await connect()
        await run_migrations(c)
        u = await UserRepository(c).upsert_google_user(
            google_id="test-upload",
            email="upload@example.com",
            name="Uploader",
        )
        await c.close()
        return u

    return asyncio.run(seed())


def test_upload_resume_deterministic_fallback(tmp_path: Path, monkeypatch):
    test_json_path = tmp_path / "data" / "profile.json"
    monkeypatch.setattr("backend.storage.profile_sync.PROFILE_JSON_PATH", test_json_path)

    # Minimal DOCX-like won't work easily; create a tiny PDF with reportlab if available,
    # otherwise skip if no sample resume exists.
    sample = (
        Path(__file__).resolve().parents[2]
        / "resume parsing agent"
        / "data"
        / "resumes"
    )
    pdfs = list(sample.glob("*.pdf")) if sample.exists() else []
    if not pdfs:
        # Create a minimal text file renamed won't parse; use pymupdf to write a page
        import fitz

        pdf_path = tmp_path / "sample.pdf"
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text(
            (72, 72),
            "Jane Doe\njane@example.com\n+1 555 0100\nSkills: Python FastAPI React\nExperience\n- Built APIs",
        )
        doc.save(pdf_path)
        doc.close()
    else:
        pdf_path = pdfs[0]

    user = _seed_user()
    token = create_access_token(user_id=user["id"], email=user["email"])
    client = TestClient(app)

    with open(pdf_path, "rb") as f:
        resp = client.post(
            "/upload-resume",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": (pdf_path.name, f, "application/pdf")},
        )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["id"] > 0
    assert data["parse_method"] in {"gemini", "deterministic"}
    assert "profile" in data
