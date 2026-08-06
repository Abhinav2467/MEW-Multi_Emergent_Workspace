import os
import pytest
from backend.config import get_settings

def test_api_key_generation(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    monkeypatch.setattr("backend.config.ENV_FILE_PATH", str(env_file))
    
    settings = get_settings()
    assert settings.api_key.startswith("mew_sk_")
    assert len(settings.api_key) == 39  # "mew_sk_" (7) + 32 hex chars
    assert env_file.exists()
    assert "MEW_API_KEY=" in env_file.read_text()
