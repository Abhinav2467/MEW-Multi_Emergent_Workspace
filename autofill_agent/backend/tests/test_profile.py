import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.config import get_settings

client = TestClient(app)

def test_profile_read_and_update():
    key = get_settings().api_key
    headers = {"X-MEW-Api-Key": key}

    # Read default profile
    res = client.get("/api/v1/profile", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert "personal" in data

    # Update profile
    updated_data = data.copy()
    updated_data["personal"]["first_name"] = "Alex"
    put_res = client.put("/api/v1/profile", json=updated_data, headers=headers)
    assert put_res.status_code == 200
    assert put_res.json()["data"]["personal"]["first_name"] == "Alex"
