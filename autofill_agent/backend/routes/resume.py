import json
from pathlib import Path
from pydantic import BaseModel
from fastapi import APIRouter
try:
    from autofill_agent.backend.utils.resume_parser import parse_resume_text
except (ModuleNotFoundError, ImportError):
    from ..utils.resume_parser import parse_resume_text

router = APIRouter(prefix="/api/v1/resume", tags=["Resume Parser"])
PROFILE_FILE = Path(__file__).resolve().parent.parent / "data" / "profile.json"

class ResumeParseRequest(BaseModel):
    text: str

@router.post("/parse")
async def parse_resume_route(payload: ResumeParseRequest):
    parsed = parse_resume_text(payload.text)
    PROFILE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PROFILE_FILE, "w") as f:
        json.dump(parsed, f, indent=2)
    return {"status": "success", "data": parsed}
