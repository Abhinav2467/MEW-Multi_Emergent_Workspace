import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.main import app
from backend.config import get_settings
from backend.schemas.autofill import FuzzyMatchResponse, FuzzyMatchItem

from backend.routes.profile import load_profile_data

client = TestClient(app)

@patch("backend.routes.autofill.match_dom_fields_with_ai")
def test_fuzzy_match_endpoint(mock_ai_match):
    profile = load_profile_data()
    expected_years = str(profile["professional"]["years_experience"])

    mock_ai_match.return_value = FuzzyMatchResponse(
        matches=[
            FuzzyMatchItem(
                element_id="custom-py-years",
                matched_key="professional.years_experience",
                value=expected_years,
                confidence=0.95,
                reasoning="Matched Python experience label."
            )
        ]
    )

    key = get_settings().api_key
    payload = {
        "fields": [
            {
                "element_id": "custom-py-years",
                "label": "Total years of Python experience?",
                "placeholder": "e.g., 5",
                "tag_name": "input",
                "input_type": "number"
            }
        ]
    }
    
    res = client.post("/api/v1/autofill-payload/match", json=payload, headers={"X-MEW-Api-Key": key})
    assert res.status_code == 200
    matches = res.json()["data"]["matches"]
    assert len(matches) == 1
    assert matches[0]["matched_key"] == "professional.years_experience"
    assert matches[0]["value"] == expected_years
