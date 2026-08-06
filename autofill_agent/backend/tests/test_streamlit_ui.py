from pathlib import Path
import pytest

def test_streamlit_app_contains_all_5_pipeline_tabs():
    app_code = Path("backend/streamlit_app.py").read_text()
    assert "Resume Parser" in app_code
    assert "Job Search" in app_code
    assert "Cold Email" in app_code
    assert "Applied Jobs Tracker" in app_code
