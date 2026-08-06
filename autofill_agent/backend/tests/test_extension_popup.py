from pathlib import Path
import pytest

def test_popup_files_exist():
    html_path = Path("extension/popup.html")
    js_path = Path("extension/popup.js")
    
    assert html_path.exists()
    assert js_path.exists()
    
    html_content = html_path.read_text()
    assert "Project MEW" in html_content
    assert "id=\"save-key-btn\"" in html_content or "saveKey" in js_path.read_text()
