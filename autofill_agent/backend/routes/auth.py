import json
import hashlib
import secrets
from pathlib import Path
from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/v1/auth", tags=["Auth Sync"])
USERS_FILE = Path(__file__).resolve().parent.parent / "data" / "users.json"

def load_users() -> dict:
    if not USERS_FILE.exists():
        return {}
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users: dict):
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def generate_user_key(email: str) -> str:
    email_hash = hashlib.sha256(email.lower().strip().encode()).hexdigest()[:12]
    random_hex = secrets.token_hex(10)
    return f"mew_sk_user_{email_hash}_{random_hex}"

from pydantic import BaseModel, Field
import os

class KeyConfigSaveRequest(BaseModel):
    google_api_key: str = Field("", description="Google Gemini API Key")

@router.get("/mock-login")
async def mock_google_login(email: str = Query(...), name: str = Query("Candidate")):
    users = load_users()
    if email not in users:
        api_key = generate_user_key(email)
        users[email] = {"name": name, "email": email, "api_key": api_key}
        save_users(users)
    else:
        api_key = users[email]["api_key"]
    return {"status": "success", "data": {"email": email, "name": name, "api_key": api_key}}

@router.post("/keys")
async def save_api_keys(request: KeyConfigSaveRequest):
    env_file = Path(__file__).resolve().parent.parent / ".env"
    lines = []
    if env_file.exists():
        with open(env_file, "r") as f:
            lines = f.readlines()

    new_lines = []
    google_found = False
    for line in lines:
        if line.startswith("GOOGLE_API_KEY="):
            new_lines.append(f"GOOGLE_API_KEY={request.google_api_key.strip()}\n")
            google_found = True
        else:
            new_lines.append(line)

    if not google_found and request.google_api_key:
        new_lines.append(f"\nGOOGLE_API_KEY={request.google_api_key.strip()}\n")

    with open(env_file, "w") as f:
        f.writelines(new_lines)

    os.environ["GOOGLE_API_KEY"] = request.google_api_key.strip()
    return {"status": "success", "message": "Google Gemini API Key saved successfully to .env and active runtime!"}
