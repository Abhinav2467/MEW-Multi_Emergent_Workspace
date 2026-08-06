import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import List
from fastapi import APIRouter
try:
    from autofill_agent.backend.schemas.applications import ApplicationLogItem, ApplicationLogResponse
except (ModuleNotFoundError, ImportError):
    from ..schemas.applications import ApplicationLogItem, ApplicationLogResponse

router = APIRouter(prefix="/api/v1/applications", tags=["Application Tracker"])
APPS_FILE = Path(__file__).resolve().parent.parent / "data" / "applications.json"

def load_applications() -> List[dict]:
    if not APPS_FILE.exists():
        return []
    try:
        with open(APPS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []

def save_applications(apps: List[dict]):
    APPS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(APPS_FILE, "w") as f:
        json.dump(apps, f, indent=2)

@router.get("", response_model=ApplicationLogResponse)
async def get_applications():
    apps = load_applications()
    return ApplicationLogResponse(data=[ApplicationLogItem(**item) for item in apps])

@router.post("/log")
async def log_application(item: ApplicationLogItem):
    apps = load_applications()
    item.id = f"app_{secrets.token_hex(6)}"
    item.timestamp = datetime.now(timezone.utc).isoformat()
    
    app_dict = item.model_dump()
    apps.append(app_dict)
    save_applications(apps)
    return {"status": "success", "data": app_dict}
