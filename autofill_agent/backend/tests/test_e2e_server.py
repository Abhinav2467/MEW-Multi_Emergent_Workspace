import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_public_test_forms_page_accessible_without_api_key():
    res = client.get("/test-forms")
    assert res.status_code == 200
    assert "Project MEW — Chrome Extension Autofill Test Suite" in res.text
    assert "DOM Event Monitor Log" in res.text

def test_autofill_preview_inspector():
    from backend.config import get_settings
    key = get_settings().api_key
    res = client.get("/autofill/preview", headers={"X-MEW-Api-Key": key})
    assert res.status_code == 200
    assert "active_profile" in res.json()["data"]
