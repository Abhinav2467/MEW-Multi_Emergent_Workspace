from pathlib import Path
import pytest

def test_content_js_contains_fuzzy_match_payload_sender():
    js_path = Path("extension/content.js")
    bg_path = Path("extension/background.js")
    assert js_path.exists()
    assert bg_path.exists()
    
    content = js_path.read_text()
    bg_content = bg_path.read_text()
    
    assert "MATCH_MEW_FIELDS" in content
    assert "/api/v1/autofill-payload/match" in bg_content
