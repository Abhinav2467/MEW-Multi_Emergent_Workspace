from pathlib import Path

import pytest

from resume_parser_agent.config import Settings
from resume_parser_agent.errors import ConfigurationError
from resume_parser_agent.startup import validate_startup_settings


def test_validate_startup_settings_creates_resume_dir(tmp_path: Path) -> None:
    resume_dir = tmp_path / "resumes"

    validate_startup_settings(Settings(resume_storage_dir=resume_dir, _env_file=None))

    assert resume_dir.exists()


def test_validate_startup_settings_requires_dashboard_password(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError):
        validate_startup_settings(
            Settings(resume_storage_dir=tmp_path, dashboard_admin_password=None, _env_file=None),
            require_dashboard_password=True,
        )


def test_validate_startup_settings_requires_gemini_key_when_fallback_enabled(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError):
        validate_startup_settings(
            Settings(
                resume_storage_dir=tmp_path,
                enable_llm_fallback=True,
                gemini_api_key=None,
                _env_file=None,
            )
        )
