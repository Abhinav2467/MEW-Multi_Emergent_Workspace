import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.auth.jwt import create_access_token

@pytest.fixture
def client():
    return TestClient(app)

def test_auth_me_with_jwt_token(client):
    """Verify that /auth/me accepts direct JWT token for instant login."""
    token = create_access_token(user_id=1, email="candidate@mew.ai")
    res = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == 1
    assert "email" in data

def test_auth_google_returns_url_with_state(client):
    """Verify /auth/google includes state when provided."""
    res = client.get("/auth/google?state=https://mew-workspace.vercel.app")
    assert res.status_code == 200
    data = res.json()
    assert "url" in data
    assert "accounts.google.com" in data["url"]
    assert "state=" in data["url"]
