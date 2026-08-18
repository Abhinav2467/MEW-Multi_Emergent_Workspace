"""Unit tests for cold email save-draft and send endpoints."""

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.auth.jwt import create_access_token


@pytest.fixture
def client():
    return TestClient(app)


def test_save_draft_unauthenticated(client):
    """Verify that calling /api/v1/emails/save-draft without Authorization header succeeds (local/guest mode)."""
    payload = {
        "company": "Nexus Corp",
        "role": "Lead Full Stack Engineer",
        "hr_email": "hr@nexuscorp.com",
        "hr_name": "Sarah Recruiter",
        "subject": "Inquiry for Lead Full Stack Engineer",
        "body": "Hello Sarah, I am writing to express my interest in Nexus Corp."
    }
    response = client.post("/api/v1/emails/save-draft", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "success"
    assert "draft_id" in data["data"]
    assert data["data"]["company"] == "Nexus Corp"


def test_save_draft_authenticated(client):
    """Verify that calling /api/v1/emails/save-draft with valid Bearer token succeeds."""
    token = create_access_token(user_id=1, email="candidate@mew.ai")
    payload = {
        "company": "Apex Dynamics",
        "role": "Senior Backend Developer",
        "hr_email": "recruiting@apexdynamics.com",
        "hr_name": "Alex Talent",
        "subject": "Inquiry for Senior Backend Developer",
        "body": "Hello Alex, I'm eager to connect regarding backend engineering."
    }
    response = client.post(
        "/api/v1/emails/save-draft",
        headers={"Authorization": f"Bearer {token}"},
        json=payload
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["company"] == "Apex Dynamics"


def test_send_email_unauthenticated(client):
    """Verify that calling /api/v1/emails/send without Authorization header succeeds."""
    payload = {
        "company": "Quantum AI",
        "role": "Staff Software Engineer",
        "to_email": "careers@quantumai.com",
        "to_name": "Jordan HR",
        "subject": "Application for Staff Software Engineer",
        "body": "Hello Jordan, please consider my application."
    }
    response = client.post("/api/v1/emails/send", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "success"
    assert data["details"]["hr_recruiter_name"] == "Jordan HR"


def test_send_email_authenticated(client):
    """Verify that calling /api/v1/emails/send with valid Bearer token succeeds."""
    token = create_access_token(user_id=1, email="candidate@mew.ai")
    payload = {
        "company": "Horizon Labs",
        "role": "AI Systems Engineer",
        "to_email": "hiring@horizonlabs.io",
        "to_name": "Morgan Recruiter",
        "subject": "Inquiry for AI Systems Engineer",
        "body": "Hello Morgan, I am reaching out regarding the AI role."
    }
    response = client.post(
        "/api/v1/emails/send",
        headers={"Authorization": f"Bearer {token}"},
        json=payload
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "success"
    assert data["details"]["hr_recruiter_name"] == "Morgan Recruiter"
