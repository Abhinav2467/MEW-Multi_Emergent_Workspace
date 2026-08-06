from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
try:
    from autofill_agent.backend.routes.profile import load_profile_data
except (ModuleNotFoundError, ImportError):
    from .profile import load_profile_data

router = APIRouter(tags=["Testing"])
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

@router.get("/test-forms", response_class=HTMLResponse)
async def get_test_forms():
    html_path = STATIC_DIR / "test_forms.html"
    with open(html_path, "r") as f:
        return f.read()

@router.get("/autofill/preview")
async def autofill_preview():
    profile = load_profile_data()
    return {
        "status": "success",
        "data": {
            "active_profile": profile,
            "inspector_note": "Post DOM descriptors to /api/v1/autofill-payload/match to test AI fuzzy mapping."
        }
    }
