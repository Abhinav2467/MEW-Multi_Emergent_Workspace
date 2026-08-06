import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_resume_parser_endpoint():
    resume_text = """
    Kamutala Abhinav Address
    Email: l4abhi@yahoo.com
    Skills: Python, HTML, SQL, Java, Machine Learning, Ethical Hacking, C++, C
    Title: Software Engineer
    Experience: 2 years
    """
    res = client.post("/api/v1/resume/parse", json={"text": resume_text})
    assert res.status_code == 200
    data = res.json()["data"]
    assert "personal" in data
    assert data["personal"]["email"] == "l4abhi@yahoo.com"
