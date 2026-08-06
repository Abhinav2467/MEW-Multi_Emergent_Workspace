from pathlib import Path
import pytest

def test_applications_tracker_tab_in_test_forms():
    html = Path("backend/static/test_forms.html").read_text()
    assert "Applied Jobs Tracker" in html
    assert "loadApplicationsTable" in html
