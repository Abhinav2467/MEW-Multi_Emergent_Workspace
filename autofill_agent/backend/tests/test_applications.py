import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_application_logging_and_retrieval():
    payload = {
        "company": "Microsoft",
        "job_title": "Software Engineer",
        "url": "https://careers.microsoft.com/us/en/job/123",
        "status": "Submitted"
    }
    log_res = client.post("/api/v1/applications/log", json=payload)
    assert log_res.status_code == 200
    assert log_res.json()["status"] == "success"
    
    get_res = client.get("/api/v1/applications")
    assert get_res.status_code == 200
    apps = get_res.json()["data"]
    assert len(apps) >= 1
    assert apps[-1]["company"] == "Microsoft"
