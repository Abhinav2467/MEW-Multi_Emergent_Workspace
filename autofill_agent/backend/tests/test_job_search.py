import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_job_search_endpoint():
    payload = {"query": "Python Developer", "location": "Remote"}
    res = client.post("/api/v1/jobs/search", json=payload)
    assert res.status_code == 200
    jobs = res.json()["data"]
    assert len(jobs) >= 1
    assert "company" in jobs[0]
