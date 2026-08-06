import json
from pathlib import Path
from fastapi import Request, HTTPException, status
from fastapi.security import APIKeyHeader
try:
    from autofill_agent.backend.config import get_settings
except (ModuleNotFoundError, ImportError):
    from backend.config import get_settings

api_key_header = APIKeyHeader(name="X-MEW-Api-Key", auto_error=False)
USERS_FILE = Path(__file__).resolve().parent.parent / "data" / "users.json"

def is_valid_user_key(key: str) -> bool:
    if not USERS_FILE.exists():
        return False
    try:
        with open(USERS_FILE, "r") as f:
            users = json.load(f)
            return any(u.get("api_key") == key for u in users.values())
    except Exception:
        return False

async def verify_api_key(request: Request):
    if request.url.path.startswith("/test-forms") or request.url.path.startswith("/static") or request.url.path.startswith("/autofill/preview") or request.url.path.startswith("/api/v1/auth") or request.url.path.startswith("/api/v1/applications") or request.url.path in ["/favicon.ico", "/docs", "/openapi.json", "/redoc"]:
        return None
    
    key = request.headers.get("X-MEW-Api-Key")
    settings = get_settings()
    
    if not key or not (key == settings.api_key or is_valid_user_key(key)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key"
        )
        
    return key
