import json
from pathlib import Path
from pydantic import BaseModel
from typing import Optional
from fastapi import APIRouter
try:
    from autofill_agent.backend.agents.cold_email_agent import generate_cold_email
except (ModuleNotFoundError, ImportError):
    from ..agents.cold_email_agent import generate_cold_email

router = APIRouter(prefix="/api/v1/email", tags=["Cold Email Agent"])
PROFILE_FILE = Path(__file__).resolve().parent.parent / "data" / "profile.json"

class ColdEmailRequest(BaseModel):
    company: str
    job_title: str
    recruiter_name: Optional[str] = "Hiring Manager"

@router.post("/generate")
async def generate_email_route(payload: ColdEmailRequest):
    profile = {}
    if PROFILE_FILE.exists():
        with open(PROFILE_FILE, "r") as f:
            profile = json.load(f)
    email_data = generate_cold_email(payload.company, payload.job_title, payload.recruiter_name or "Hiring Manager", profile)
    return {"status": "success", "data": email_data}
