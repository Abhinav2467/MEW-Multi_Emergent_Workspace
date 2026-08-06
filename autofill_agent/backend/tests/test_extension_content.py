from pathlib import Path
import pytest

def test_content_script_and_styles_exist():
    css_path = Path("extension/styles.css")
    js_path = Path("extension/content.js")
    
    assert css_path.exists()
    assert js_path.exists()
    
    css_content = css_path.read_text()
    assert "#mew-autofill-badge" in css_content
    
    js_content = js_path.read_text()
    assert "dispatchEvent" in js_content
    assert "focus" in js_content
    assert "input" in js_content
    assert "change" in js_content
    assert "blur" in js_content
