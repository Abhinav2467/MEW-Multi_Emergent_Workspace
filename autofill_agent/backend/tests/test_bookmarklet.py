import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_bookmarklet_static_file_accessible():
    res = client.get("/static/mew_bookmarklet.js")
    assert res.status_code == 200
    assert "mew-autofill-badge" in res.text
    assert "fillAndDispatch" in res.text
