import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.config import get_settings

from backend.routes.profile import load_profile_data

client = TestClient(app)

def test_get_autofill_payload():
    key = get_settings().api_key
    res = client.get("/api/v1/autofill-payload", headers={"X-MEW-Api-Key": key})
    assert res.status_code == 200
    json_res = res.json()
    assert json_res["status"] == "success"
    payload = json_res["data"]
    assert "event_hints" in payload
    assert payload["event_hints"]["dispatch_sequence"] == ["focus", "input", "change", "blur"]
    profile = load_profile_data()
    assert payload["personal"]["email"] == profile["personal"]["email"]
