from pathlib import Path
import pytest

def test_client_scripts_contain_whole_form_ai_dispatcher():
    content_js = Path("extension/content.js").read_text()
    bookmarklet_js = Path("backend/static/mew_bookmarklet.js").read_text()
    
    assert "MATCH_MEW_FIELDS" in content_js
    assert "/api/v1/autofill-payload/match" in bookmarklet_js
    assert "domFields" in bookmarklet_js or "domFields" in content_js
