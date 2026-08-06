# MEW Autofill Backend & Verification Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a secure, high-performance FastAPI backend for Project MEW Autofill, featuring pre-normalized payload delivery, `gemini-1.5-flash` fuzzy DOM field matching, `X-MEW-Api-Key` authentication, and an interactive `/test-forms` verification suite.

**Architecture:** A modular FastAPI micro-service structure with distinct security middleware (`auth.py`), agent reasoning (`autofill_agent.py`), profile persistence (`profile.json`), payload delivery routes (`autofill.py`), and a self-contained HTML/JS test runner (`test_forms.html`).

**Tech Stack:** Python 3.12+, FastAPI, Uvicorn, Pydantic v2, LangChain (`langchain-google-genai`), Pytest, HTML5/CSS3/JS.

## Global Constraints

- **Directory:** All backend code resides inside `backend/`.
- **Security:** Every `/api/v1/*` endpoint MUST require header `X-MEW-Api-Key` and enforce 60 req/min rate limits.
- **Testing:** Every task must follow strict TDD (write failing test, run, implement minimal code, verify pass, commit).

---

### Task 1: Environment & API Key Security Provisioning

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/config.py`
- Create: `backend/tests/test_config.py`

**Interfaces:**
- Consumes: Environment variables / `.env`
- Produces: `get_settings()` returning `Settings(api_key: str, env: str)` with automatic 32-character key generation if missing.

- [ ] **Step 1: Write failing test for config & key generation**

```python
# backend/tests/test_config.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_config.py -v`  
Expected: FAIL (ModuleNotFoundError: No module named 'backend')

- [ ] **Step 3: Write minimal implementation for requirements & config**

```python
# backend/config.py
import os
import secrets
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE_PATH = os.getenv("MEW_ENV_FILE", str(BASE_DIR / ".env"))

class Settings(BaseSettings):
    api_key: str = ""
    environment: str = "development"
    google_api_key: str = ""

    class Config:
        env_file = ".env"

def get_settings() -> Settings:
    env_path = Path(ENV_FILE_PATH)
    current_key = os.getenv("MEW_API_KEY", "")
    
    if not current_key and env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                if line.startswith("MEW_API_KEY="):
                    current_key = line.strip().split("=", 1)[1]
                    break

    if not current_key:
        generated_key = f"mew_sk_{secrets.token_hex(16)}"
        with open(env_path, "a" if env_path.exists() else "w") as f:
            f.write(f"\nMEW_API_KEY={generated_key}\n")
        current_key = generated_key

    return Settings(api_key=current_key)
```

```text
# backend/requirements.txt
fastapi>=0.110.0
uvicorn>=0.28.0
pydantic>=2.6.0
pydantic-settings>=2.2.0
langchain>=0.1.0
langchain-google-genai>=0.0.10
python-dotenv>=1.0.1
httpx>=0.27.0
pytest>=8.0.0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_config.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/requirements.txt backend/config.py backend/tests/test_config.py
git commit -m "feat: add config management and automatic API key provisioning"
```

---

### Task 2: Security Middleware (Authentication & Rate Limiting)

**Files:**
- Create: `backend/security/auth.py`
- Create: `backend/security/rate_limiter.py`
- Create: `backend/tests/test_auth.py`
- Create: `backend/main.py`

**Interfaces:**
- Consumes: `get_settings().api_key`
- Produces: `APIKeyMiddleware` enforcing `X-MEW-Api-Key` and CORS boundaries on FastAPI `app`.

- [ ] **Step 1: Write failing test for Security Middleware**

```python
# backend/tests/test_auth.py
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.config import get_settings

client = TestClient(app)

def test_unauthorized_request_fails():
    response = client.get("/api/v1/profile")
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing or invalid API key"

def test_authorized_request_succeeds():
    settings = get_settings()
    response = client.get("/api/v1/profile", headers={"X-MEW-Api-Key": settings.api_key})
    assert response.status_code == 200

def test_cors_headers_allowed():
    response = client.options(
        "/api/v1/profile",
        headers={"Origin": "chrome-extension://abcdefg", "Access-Control-Request-Method": "GET"}
    )
    assert response.headers.get("access-control-allow-origin") == "chrome-extension://abcdefg"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_auth.py -v`  
Expected: FAIL (main.py does not exist yet)

- [ ] **Step 3: Write minimal security middleware & FastAPI app**

```python
# backend/security/auth.py
from fastapi import Request, HTTPException, status
from fastapi.security import APIKeyHeader
from backend.config import get_settings

api_key_header = APIKeyHeader(name="X-MEW-Api-Key", auto_error=False)

async def verify_api_key(request: Request):
    # Skip auth for public static test forms and docs
    if request.url.path.startswith("/test-forms") or request.url.path in ["/docs", "/openapi.json", "/redoc"]:
        return None
    
    key = request.headers.get("X-MEW-Api-Key")
    settings = get_settings()
    if not key or key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key"
        )
    return key
```

```python
# backend/security/rate_limiter.py
import time
from fastapi import Request, HTTPException, status

class RateLimiter:
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}

    def check_rate_limit(self, request: Request):
        client_ip = request.client.host if request.client else "127.0.0.1"
        now = time.time()
        
        # Clean expired timestamps
        timestamps = [t for t in self.requests.get(client_ip, []) if now - t < self.window_seconds]
        if len(timestamps) >= self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Maximum 60 requests per minute."
            )
        timestamps.append(now)
        self.requests[client_ip] = timestamps
```

```python
# backend/main.py
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from backend.security.auth import verify_api_key
from backend.security.rate_limiter import RateLimiter

limiter = RateLimiter(max_requests=60, window_seconds=60)

app = FastAPI(
    title="Project MEW Autofill Backend API",
    version="1.0.0",
    dependencies=[Depends(verify_api_key)]
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"chrome-extension://.*|http://localhost:.*|http://127\.0\.0\.1:.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def rate_limit_middleware(request, call_next):
    if not request.url.path.startswith("/test-forms"):
        limiter.check_rate_limit(request)
    response = await call_next(request)
    return response

@app.get("/api/v1/profile")
async def get_profile_stub():
    return {"status": "success", "data": {}}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_auth.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/security/ backend/main.py backend/tests/test_auth.py
git commit -m "feat: implement API key security middleware, rate limiter, and CORS boundaries"
```

---

### Task 3: Candidate Profile Pydantic Schemas & Persistence Engine

**Files:**
- Create: `backend/schemas/profile.py`
- Create: `backend/data/profile.json`
- Create: `backend/routes/profile.py`
- Create: `backend/tests/test_profile.py`

**Interfaces:**
- Consumes: JSON input from Resume Parser or manual uploads.
- Produces: `GET /api/v1/profile` and `PUT /api/v1/profile` managing persistent `backend/data/profile.json`.

- [ ] **Step 1: Write failing test for Profile Storage & Routes**

```python
# backend/tests/test_profile.py
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.config import get_settings

client = TestClient(app)

def test_profile_read_and_update():
    key = get_settings().api_key
    headers = {"X-MEW-Api-Key": key}

    # Read default profile
    res = client.get("/api/v1/profile", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert "personal" in data

    # Update profile
    updated_data = data.copy()
    updated_data["personal"]["first_name"] = "Alex"
    put_res = client.put("/api/v1/profile", json=updated_data, headers=headers)
    assert put_res.status_code == 200
    assert put_res.json()["data"]["personal"]["first_name"] == "Alex"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_profile.py -v`  
Expected: FAIL (routes/profile.py not connected)

- [ ] **Step 3: Write profile schemas, default seed data, and routes**

```python
# backend/schemas/profile.py
from typing import List, Dict, Optional
from pydantic import BaseModel, EmailStr, HttpUrl

class PersonalProfile(BaseModel):
    first_name: str
    last_name: str
    full_name: str
    email: EmailStr
    phone: str
    linkedin_url: Optional[str] = ""
    github_url: Optional[str] = ""
    portfolio_url: Optional[str] = ""
    location: str
    work_authorization: str

class ProfessionalProfile(BaseModel):
    current_title: str
    years_experience: int
    primary_skills: List[str]
    summary: str

class CandidateProfile(BaseModel):
    personal: PersonalProfile
    professional: ProfessionalProfile
    custom_qa: Dict[str, str] = {}
```

```json
// backend/data/profile.json
{
  "personal": {
    "first_name": "Jane",
    "last_name": "Doe",
    "full_name": "Jane Doe",
    "email": "jane.doe@example.com",
    "phone": "+15550199823",
    "linkedin_url": "https://linkedin.com/in/janedoe",
    "github_url": "https://github.com/janedoe",
    "portfolio_url": "https://janedoe.dev",
    "location": "San Francisco, CA",
    "work_authorization": "US Citizen"
  },
  "professional": {
    "current_title": "Senior Software Engineer",
    "years_experience": 6,
    "primary_skills": ["Python", "FastAPI", "React", "TypeScript", "LangChain"],
    "summary": "Experienced software engineer specializing in backend systems and AI agent orchestration."
  },
  "custom_qa": {
    "willing_to_relocate": "Yes",
    "notice_period": "2 weeks",
    "desired_salary": "$150,000"
  }
}
```

```python
# backend/routes/profile.py
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from backend.schemas.profile import CandidateProfile

router = APIRouter(prefix="/api/v1", tags=["Profile"])
PROFILE_PATH = Path(__file__).resolve().parent.parent / "data" / "profile.json"

def load_profile_data() -> dict:
    if not PROFILE_PATH.exists():
        return {}
    with open(PROFILE_PATH, "r") as f:
        return json.load(f)

def save_profile_data(data: dict):
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PROFILE_PATH, "w") as f:
        json.dump(data, f, indent=2)

@router.get("/profile")
async def get_profile():
    data = load_profile_data()
    return {"status": "success", "data": data}

@router.put("/profile")
async def update_profile(profile: CandidateProfile):
    save_profile_data(profile.model_dump())
    return {"status": "success", "data": profile.model_dump()}
```

Include route in `backend/main.py`:
```python
# backend/main.py
from backend.routes.profile import router as profile_router
app.include_router(profile_router)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_profile.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/schemas/profile.py backend/data/profile.json backend/routes/profile.py backend/main.py backend/tests/test_profile.py
git commit -m "feat: add CandidateProfile schemas, persistent JSON engine, and profile routes"
```

---

### Task 4: Normalized Autofill Payload API (`GET /api/v1/autofill-payload`)

**Files:**
- Create: `backend/schemas/autofill.py`
- Create: `backend/routes/autofill.py`
- Create: `backend/tests/test_autofill_payload.py`

**Interfaces:**
- Consumes: Active candidate profile data from `load_profile_data()`.
- Produces: `GET /api/v1/autofill-payload` returning pre-normalized autofill values with synthetic event hints.

- [ ] **Step 1: Write failing test for Normalized Payload Route**

```python
# backend/tests/test_autofill_payload.py
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.config import get_settings

client = TestClient(app)

def test_get_autofill_payload():
    key = get_settings().api_key
    res = client.get("/api/v1/autofill-payload", headers={"X-MEW-Api-Key": key})
    assert res.status_code == 200
    json_res = res.json()
    assert json_res["status"] == "success"
    payload = json_res["data"]
    assert "event_hints" in payload
    assert payload["event_hints"]["dispatch_sequence"] == ["focus", "input", "change", "blur"]
    assert payload["personal"]["email"] == "jane.doe@example.com"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_autofill_payload.py -v`  
Expected: FAIL (routes/autofill.py not created)

- [ ] **Step 3: Write payload schema & route implementation**

```python
# backend/schemas/autofill.py
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class EventHints(BaseModel):
    dispatch_sequence: List[str] = ["focus", "input", "change", "blur"]
    simulate_synthetic_events: bool = True

class DOMFieldDescriptor(BaseModel):
    element_id: str
    label: str = ""
    placeholder: str = ""
    tag_name: str = "input"
    input_type: str = "text"

class FuzzyMatchRequest(BaseModel):
    fields: List[DOMFieldDescriptor]

class FuzzyMatchItem(BaseModel):
    element_id: str
    matched_key: str
    value: str
    confidence: float
    reasoning: str

class FuzzyMatchResponse(BaseModel):
    matches: List[FuzzyMatchItem]
```

```python
# backend/routes/autofill.py
from fastapi import APIRouter
from backend.routes.profile import load_profile_data
from backend.schemas.autofill import EventHints

router = APIRouter(prefix="/api/v1", tags=["Autofill"])

@router.get("/autofill-payload")
async def get_autofill_payload():
    profile = load_profile_data()
    payload = profile.copy()
    payload["event_hints"] = EventHints().model_dump()
    return {"status": "success", "data": payload}
```

Include route in `backend/main.py`:
```python
from backend.routes.autofill import router as autofill_router
app.include_router(autofill_router)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_autofill_payload.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/schemas/autofill.py backend/routes/autofill.py backend/main.py backend/tests/test_autofill_payload.py
git commit -m "feat: add GET /api/v1/autofill-payload route with synthetic event hints"
```

---

### Task 5: AI-Assisted Fuzzy Field Matcher (`POST /api/v1/autofill-payload/match`)

**Files:**
- Create: `backend/agents/autofill_agent.py`
- Modify: `backend/routes/autofill.py`
- Create: `backend/tests/test_fuzzy_match.py`

**Interfaces:**
- Consumes: `FuzzyMatchRequest` (DOM field descriptors) and active candidate profile.
- Produces: `POST /api/v1/autofill-payload/match` returning `FuzzyMatchResponse`.

- [ ] **Step 1: Write failing test for Fuzzy Field Matcher**

```python
# backend/tests/test_fuzzy_match.py
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from backend.main import app
from backend.config import get_settings
from backend.schemas.autofill import FuzzyMatchResponse, FuzzyMatchItem

client = TestClient(app)

@patch("backend.agents.autofill_agent.match_dom_fields_with_ai")
def test_fuzzy_match_endpoint(mock_ai_match):
    mock_ai_match.return_value = FuzzyMatchResponse(
        matches=[
            FuzzyMatchItem(
                element_id="custom-py-years",
                matched_key="professional.years_experience",
                value="6",
                confidence=0.95,
                reasoning="Matched Python experience label."
            )
        ]
    )

    key = get_settings().api_key
    payload = {
        "fields": [
            {
                "element_id": "custom-py-years",
                "label": "Total years of Python experience?",
                "placeholder": "e.g., 5",
                "tag_name": "input",
                "input_type": "number"
            }
        ]
    }
    
    res = client.post("/api/v1/autofill-payload/match", json=payload, headers={"X-MEW-Api-Key": key})
    assert res.status_code == 200
    matches = res.json()["data"]["matches"]
    assert len(matches) == 1
    assert matches[0]["matched_key"] == "professional.years_experience"
    assert matches[0]["value"] == "6"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_fuzzy_match.py -v`  
Expected: FAIL (agent and match endpoint not implemented)

- [ ] **Step 3: Implement LangChain + Gemini 1.5 Flash agent & POST route**

```python
# backend/agents/autofill_agent.py
import os
from typing import List, Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from backend.schemas.autofill import DOMFieldDescriptor, FuzzyMatchResponse, FuzzyMatchItem

def match_dom_fields_with_ai(fields: List[DOMFieldDescriptor], profile_data: Dict[str, Any]) -> FuzzyMatchResponse:
    google_key = os.getenv("GOOGLE_API_KEY", "")
    
    # Fallback heuristic if no Google API key is set
    if not google_key:
        matches = []
        for field in fields:
            label_lower = field.label.lower()
            val = ""
            matched_key = "unknown"
            
            if "python" in label_lower or "experience" in label_lower:
                val = str(profile_data.get("professional", {}).get("years_experience", 5))
                matched_key = "professional.years_experience"
            elif "relocate" in label_lower:
                val = profile_data.get("custom_qa", {}).get("willing_to_relocate", "Yes")
                matched_key = "custom_qa.willing_to_relocate"
            else:
                val = profile_data.get("personal", {}).get("full_name", "")
                matched_key = "personal.full_name"
                
            matches.append(FuzzyMatchItem(
                element_id=field.element_id,
                matched_key=matched_key,
                value=val,
                confidence=0.85,
                reasoning="Heuristic keyword fallback matching."
            ))
        return FuzzyMatchResponse(matches=matches)

    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=google_key)
    structured_llm = llm.with_structured_output(FuzzyMatchResponse)

    prompt = f"""
You are an expert AI form-autofill assistant.
Match the following DOM form fields to the most appropriate value in the Candidate Profile.

Candidate Profile:
{profile_data}

DOM Fields to Match:
{[f.model_dump() for f in fields]}

Return the matched fields with confidence score (0.0 to 1.0) and reasoning.
"""
    return structured_llm.invoke(prompt)
```

Modify `backend/routes/autofill.py`:
```python
from backend.schemas.autofill import FuzzyMatchRequest
from backend.agents.autofill_agent import match_dom_fields_with_ai

@router.post("/autofill-payload/match")
async def match_autofill_fields(request: FuzzyMatchRequest):
    profile = load_profile_data()
    match_response = match_dom_fields_with_ai(request.fields, profile)
    return {"status": "success", "data": match_response.model_dump()}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_fuzzy_match.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/agents/autofill_agent.py backend/routes/autofill.py backend/tests/test_fuzzy_match.py
git commit -m "feat: implement AI-assisted fuzzy field matcher with gemini-1.5-flash and heuristic fallback"
```

---

### Task 6: Interactive Testing Suite (`/test-forms`) & Event Log Monitor

**Files:**
- Create: `backend/static/test_forms.html`
- Create: `backend/routes/testing.py`
- Modify: `backend/main.py`
- Create: `backend/tests/test_e2e_server.py`

**Interfaces:**
- Consumes: Static HTML/JS test runner.
- Produces: Public endpoint `GET /test-forms` and Inspector `/autofill/preview`.

- [ ] **Step 1: Write failing test for Test Suite Endpoints**

```python
# backend/tests/test_e2e_server.py
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_public_test_forms_page_accessible_without_api_key():
    res = client.get("/test-forms")
    assert res.status_code == 200
    assert "Project MEW — Chrome Extension Autofill Test Suite" in res.text
    assert "DOM Event Monitor Log" in res.text

def test_autofill_preview_inspector():
    from backend.config import get_settings
    key = get_settings().api_key
    res = client.get("/autofill/preview", headers={"X-MEW-Api-Key": key})
    assert res.status_code == 200
    assert "active_profile" in res.json()["data"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_e2e_server.py -v`  
Expected: FAIL (test_forms.html and routes/testing.py do not exist)

- [ ] **Step 3: Create static test runner HTML and testing routes**

```html
<!-- backend/static/test_forms.html -->
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Project MEW — Chrome Extension Autofill Test Suite</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 20px; }
    .container { max-width: 900px; margin: 0 auto; }
    h1 { color: #38bdf8; font-size: 24px; }
    .tab-bar { display: flex; gap: 10px; margin-bottom: 20px; border-bottom: 2px solid #334155; }
    .tab-btn { background: #1e293b; color: #94a3b8; border: none; padding: 10px 18px; cursor: pointer; border-radius: 6px 6px 0 0; }
    .tab-btn.active { background: #38bdf8; color: #0f172a; font-weight: bold; }
    .form-card { background: #1e293b; padding: 24px; border-radius: 8px; border: 1px solid #334155; display: none; }
    .form-card.active { display: block; }
    .form-group { margin-bottom: 16px; }
    label { display: block; margin-bottom: 6px; font-size: 14px; color: #cbd5e1; }
    input, textarea, select { width: 100%; padding: 10px; border-radius: 6px; border: 1px solid #475569; background: #0f172a; color: #f8fafc; box-sizing: border-box; }
    .log-panel { margin-top: 30px; background: #020617; border: 1px solid #334155; border-radius: 8px; padding: 16px; }
    .log-title { font-size: 14px; font-weight: bold; color: #f59e0b; margin-bottom: 10px; }
    #event-log { font-family: monospace; font-size: 12px; max-height: 180px; overflow-y: auto; color: #4ade80; margin: 0; padding: 0; list-style: none; }
  </style>
</head>
<body>
  <div class="container">
    <h1>Project MEW — Autofill Test Runner</h1>
    <div class="tab-bar">
      <button class="tab-btn active" onclick="showTab(1)">1. Standard App</button>
      <button class="tab-btn" onclick="showTab(2)">2. React State</button>
      <button class="tab-btn" onclick="showTab(3)">3. Custom QA</button>
      <button class="tab-btn" onclick="showTab(4)">4. Multi-Step Wizard</button>
      <button class="tab-btn" onclick="showTab(5)">5. Shadow DOM</button>
    </div>

    <!-- Form 1 -->
    <div id="form-1" class="form-card active">
      <h3>Scenario 1: Standard Job Application</h3>
      <form>
        <div class="form-group"><label>First Name</label><input type="text" name="first_name" id="first_name" autocomplete="given-name"></div>
        <div class="form-group"><label>Last Name</label><input type="text" name="last_name" id="last_name" autocomplete="family-name"></div>
        <div class="form-group"><label>Email Address</label><input type="email" name="email" id="email" autocomplete="email"></div>
        <div class="form-group"><label>Phone Number</label><input type="tel" name="phone" id="phone" autocomplete="tel"></div>
      </form>
    </div>

    <!-- Form 2 -->
    <div id="form-2" class="form-card">
      <h3>Scenario 2: React Controlled Inputs</h3>
      <div class="form-group"><label>Full Name (React Binding)</label><input type="text" id="react-name" placeholder="John Doe"></div>
      <div class="form-group"><label>LinkedIn Profile URL</label><input type="url" id="react-linkedin" placeholder="https://linkedin.com/in/username"></div>
    </div>

    <!-- Form 3 -->
    <div id="form-3" class="form-card">
      <h3>Scenario 3: Custom QA & Ambiguous Fields</h3>
      <div class="form-group"><label>Total years of Python experience?</label><input type="number" id="custom-py-years" placeholder="e.g. 5"></div>
      <div class="form-group"><label>Are you willing to relocate?</label><input type="text" id="custom-relocate" placeholder="Yes / No"></div>
    </div>

    <!-- Form 4 -->
    <div id="form-4" class="form-card">
      <h3>Scenario 4: Multi-Step Application Wizard (Step 1)</h3>
      <div class="form-group"><label>Current Job Title</label><input type="text" id="wizard-title"></div>
    </div>

    <!-- Form 5 -->
    <div id="form-5" class="form-card">
      <h3>Scenario 5: Encapsulated Shadow DOM Form</h3>
      <div id="shadow-host"></div>
    </div>

    <!-- Event Monitor -->
    <div class="log-panel">
      <div class="log-title">DOM Event Monitor Log (Simulated Synthetic Events)</div>
      <ul id="event-log"><li>[System] Ready to capture input, change, focus, and blur events...</li></ul>
    </div>
  </div>

  <script>
    function showTab(num) {
      document.querySelectorAll('.tab-btn').forEach((b, i) => b.classList.toggle('active', i === num - 1));
      document.querySelectorAll('.form-card').forEach((f, i) => f.classList.toggle('active', i === num - 1));
    }

    // Attach Event Monitor
    ['focus', 'input', 'change', 'blur'].forEach(eventType => {
      document.addEventListener(eventType, (e) => {
        if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) {
          const log = document.getElementById('event-log');
          const li = document.createElement('li');
          li.textContent = `[${new Date().toLocaleTimeString()}] Event: '${eventType}' on #${e.target.id || e.target.name || 'field'} | Value: "${e.target.value}"`;
          log.prepend(li);
        }
      }, true);
    });

    // Shadow DOM Setup
    const host = document.getElementById('shadow-host');
    if (host) {
      const root = host.attachShadow({mode: 'open'});
      root.innerHTML = `<style>label{color:#cbd5e1;display:block;margin-bottom:6px;}input{width:100%;padding:10px;border-radius:6px;border:1px solid #475569;background:#0f172a;color:#fff;}</style><div><label>Portfolio / Personal Website (Inside Shadow DOM)</label><input type="url" id="shadow-portfolio"></div>`;
    }
  </script>
</body>
</html>
```

```python
# backend/routes/testing.py
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from backend.routes.profile import load_profile_data

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
```

Include routes in `backend/main.py`:
```python
from backend.routes.testing import router as testing_router
app.include_router(testing_router)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_e2e_server.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/static/test_forms.html backend/routes/testing.py backend/main.py backend/tests/test_e2e_server.py
git commit -m "feat: add interactive /test-forms runner with synthetic event monitor and /autofill/preview inspector"
```

---

## Plan Self-Review Checklist

- **Spec coverage:** Config & Security (Task 1, 2), Profile Engine (Task 3), Pre-normalized Payload (Task 4), AI Fuzzy Field Matcher (Task 5), Test Suite Runner (Task 6).
- **Placeholder scan:** No TBDs, TODOs, or missing code blocks.
- **Type consistency:** Matches all schema names (`CandidateProfile`, `DOMFieldDescriptor`, `FuzzyMatchRequest`, `FuzzyMatchResponse`).
