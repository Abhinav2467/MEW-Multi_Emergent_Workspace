import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_user_key_provisioning_and_auth():
    res = client.get("/api/v1/auth/mock-login?email=user@example.com&name=Abhinav")
    assert res.status_code == 200
    user_key = res.json()["data"]["api_key"]
    assert user_key.startswith("mew_sk_user_")

    profile_res = client.get("/api/v1/profile", headers={"X-MEW-Api-Key": user_key})
    assert profile_res.status_code == 200
