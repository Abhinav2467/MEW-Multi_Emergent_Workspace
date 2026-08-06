from pathlib import Path
import pytest

def test_bookmarklet_button_in_test_forms():
    html_path = Path("backend/static/test_forms.html")
    assert html_path.exists()
    content = html_path.read_text()
    assert "javascript:(function()" in content
    assert "Drag to Bookmarks Bar" in content
