from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter
try:
    from autofill_agent.backend.agents.job_search_agent import search_jobs_with_ai
except (ModuleNotFoundError, ImportError):
    from backend.agents.job_search_agent import search_jobs_with_ai

router = APIRouter(prefix="/api/v1/jobs", tags=["Job Search Agent"])

class JobSearchRequest(BaseModel):
    query: str = "Software Engineer"
    location: Optional[str] = "Remote"

@router.post("/search")
async def job_search_route(payload: JobSearchRequest):
    jobs = search_jobs_with_ai(payload.query, payload.location or "Remote")
    return {"status": "success", "data": jobs}
