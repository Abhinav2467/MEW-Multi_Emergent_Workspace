import json
from pathlib import Path
import pytest

MANIFEST_PATH = Path("extension/manifest.json")

def test_manifest_v3_structure():
    assert MANIFEST_PATH.exists()
    with open(MANIFEST_PATH, "r") as f:
        data = json.load(f)
    assert data["manifest_version"] == 3
    assert data["name"] == "Project MEW — Job Application Autofill"
    assert "activeTab" in data["permissions"]
    assert "storage" in data["permissions"]
    assert "<all_urls>" in data["host_permissions"]
    assert data["background"]["service_worker"] == "background.js"
