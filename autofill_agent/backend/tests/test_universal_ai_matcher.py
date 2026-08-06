import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.main import app
from backend.config import get_settings
from backend.schemas.autofill import DOMFieldDescriptor, FuzzyMatchResponse, FuzzyMatchItem
from backend.agents.autofill_agent import match_dom_fields_with_ai

client = TestClient(app)

@patch("backend.routes.autofill.match_dom_fields_with_ai")
def test_universal_ai_dom_matching(mock_ai):
    mock_ai.return_value = FuzzyMatchResponse(
        matches=[
            FuzzyMatchItem(element_id="first_name", matched_key="personal.first_name", value="Kamutala", confidence=0.99, reasoning="Matched first name"),
            FuzzyMatchItem(element_id="email", matched_key="personal.email", value="l4abhi@yahoo.com", confidence=0.99, reasoning="Matched email"),
            FuzzyMatchItem(element_id="custom-py", matched_key="professional.primary_skills", value="Python, HTML, SQL", confidence=0.92, reasoning="Matched skills")
        ]
    )
    
    key = get_settings().api_key
    payload = {
        "fields": [
            {"element_id": "first_name", "label": "First Name", "placeholder": "Jane", "tag_name": "input", "input_type": "text"},
            {"element_id": "email", "label": "Email Address", "placeholder": "jane@example.com", "tag_name": "input", "input_type": "email"},
            {"element_id": "custom-py", "label": "List your core technical skills", "placeholder": "e.g. Python", "tag_name": "textarea", "input_type": "text"}
        ]
    }
    
    res = client.post("/api/v1/autofill-payload/match", json=payload, headers={"X-MEW-Api-Key": key})
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data["matches"]) == 3
    assert data["matches"][0]["value"] == "Kamutala"

def test_heuristic_fallback_matching():
    fields = [
        DOMFieldDescriptor(element_id="first_name", label="First Name", placeholder="Jane", tag_name="input", input_type="text"),
        DOMFieldDescriptor(element_id="email", label="Email Address", placeholder="jane@example.com", tag_name="input", input_type="email"),
        DOMFieldDescriptor(element_id="custom-py", label="List your core technical skills", placeholder="e.g. Python", tag_name="textarea", input_type="text"),
    ]
    profile_data = {
        "personal": {"first_name": "Kamutala", "email": "l4abhi@yahoo.com"},
        "professional": {"primary_skills": ["Python", "HTML", "SQL"]}
    }
    with patch.dict("os.environ", {"GOOGLE_API_KEY": ""}):
        res = match_dom_fields_with_ai(fields, profile_data)
        assert len(res.matches) == 3
        assert res.matches[0].element_id == "first_name"
        assert res.matches[0].value == "Kamutala"
        assert res.matches[1].value == "l4abhi@yahoo.com"
        assert res.matches[2].value == "Python, HTML, SQL"
