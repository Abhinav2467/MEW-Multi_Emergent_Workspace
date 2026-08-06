from pathlib import Path
import pytest

def test_auto_apply_script_contains_submit_detector_and_logger():
    content_js = Path("extension/content.js").read_text()
    bookmarklet_js = Path("backend/static/mew_bookmarklet.js").read_text()
    
    assert "logApplication" in content_js or "/api/v1/applications/log" in content_js
    assert "/api/v1/applications/log" in bookmarklet_js
    assert "Submit" in bookmarklet_js or "Submit" in content_js
