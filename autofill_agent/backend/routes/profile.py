import json
from pathlib import Path
from fastapi import APIRouter, Body
from typing import Any, Dict

router = APIRouter(prefix="/api/v1", tags=["Profile"])
PROFILE_PATH = Path(__file__).resolve().parent.parent / "data" / "profile.json"

def load_profile_data() -> dict:
    if not PROFILE_PATH.exists():
        return {}
    try:
        with open(PROFILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_profile_data(data: dict):
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PROFILE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

@router.get("/profile")
async def get_profile():
    data = load_profile_data()
    return {"status": "success", "data": data}

@router.put("/profile")
async def update_profile(payload: Dict[str, Any] = Body(...)):
    existing = load_profile_data()
    if not existing:
        existing = {"personal": {}, "professional": {}, "custom_qa": {}}

    personal = existing.get("personal", {})
    professional = existing.get("professional", {})

    full_name = payload.get("name") or payload.get("full_name") or personal.get("full_name") or ""
    parts = full_name.strip().split(" ")
    first_name = parts[0] if parts else ""
    last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

    personal["full_name"] = full_name
    personal["first_name"] = first_name
    personal["last_name"] = last_name
    if "email" in payload:
        personal["email"] = payload["email"]
    if "phone" in payload:
        personal["phone"] = payload["phone"]
    if "location" in payload:
        personal["location"] = payload["location"]
    if "current_title" in payload:
        professional["current_title"] = payload["current_title"]
    if "skills" in payload:
        professional["primary_skills"] = payload["skills"]

    existing["personal"] = personal
    existing["professional"] = professional

    save_profile_data(existing)
    return {"status": "success", "data": existing}
