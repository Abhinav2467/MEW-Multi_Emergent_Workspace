import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.config import get_settings

client = TestClient(app)

def test_unauthorized_request_fails():
    response = client.get("/api/v1/profile")
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing or invalid API key"

def test_authorized_request_succeeds():
    settings = get_settings()
    response = client.get("/api/v1/profile", headers={"X-MEW-Api-Key": settings.api_key})
    assert response.status_code == 200

def test_cors_headers_allowed():
    response = client.options(
        "/api/v1/profile",
        headers={"Origin": "chrome-extension://abcdefg", "Access-Control-Request-Method": "GET"}
    )
    assert response.headers.get("access-control-allow-origin") == "chrome-extension://abcdefg"
