import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_cold_email_endpoint():
    payload = {
        "company": "Microsoft",
        "job_title": "Software Engineer",
        "recruiter_name": "Sarah Smith"
    }
    res = client.post("/api/v1/email/generate", json=payload)
    assert res.status_code == 200
    data = res.json()["data"]
    assert "subject" in data
    assert "body" in data
    assert "Microsoft" in data["body"]
