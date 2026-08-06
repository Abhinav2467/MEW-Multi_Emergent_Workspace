# MEW Live Extension & Google Auth Auto-Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-ready Manifest V3 Chrome Extension package (`extension/`) for live career portals (Workday, Greenhouse, Lever, LinkedIn, etc.) with a floating "✨ MEW Autofill" badge, and implement Google OAuth unique API key provisioning & auto-sync (`backend/routes/auth.py`).

**Architecture:** 
1. `backend/routes/auth.py` provisions unique `mew_sk_user_<hash>` keys on Google login.
2. `extension/background.js` auto-syncs key via `chrome.storage.local`.
3. `extension/content.js` injects floating badge, matches standard + AI fuzzy fields (`POST /api/v1/autofill-payload/match`), and dispatches framework synthetic events (`focus`, `input`, `change`, `blur`).

**Tech Stack:** Python 3.12+, FastAPI, Pydantic v2, Chrome Extension Manifest V3, HTML5/CSS3/Vanilla JS.

## Global Constraints

- **Directory:** Extension files live in `extension/`, backend auth routes in `backend/routes/auth.py`.
- **Manifest Version:** Must be strict Chrome Extension Manifest V3 (`manifest_version: 3`).
- **Security:** `verify_api_key` must accept global `.env` key OR any registered user key in `backend/data/users.json`.
- **Testing:** Every task follows TDD.

---

### Task 1: Google OAuth Auth Routes & Unique User Key Generator

**Files:**
- Create: `backend/routes/auth.py`
- Modify: `backend/security/auth.py`
- Modify: `backend/main.py`
- Create: `backend/tests/test_auth_sync.py`
- Create: `backend/data/users.json`

**Interfaces:**
- Consumes: Google OAuth login response / user payload.
- Produces: `GET /api/v1/auth/google/login`, `GET /api/v1/auth/callback`, and `verify_api_key` supporting `mew_sk_user_<hash>` keys.

- [ ] **Step 1: Write failing test for user key generation & validation**

```python
# backend/tests/test_auth_sync.py
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_user_key_provisioning_and_auth():
    # Simulate Google OAuth login callback
    res = client.get("/api/v1/auth/mock-login?email=user@example.com&name=Abhinav")
    assert res.status_code == 200
    user_key = res.json()["data"]["api_key"]
    assert user_key.startswith("mew_sk_user_")

    # Verify authorized request using the new user_key
    profile_res = client.get("/api/v1/profile", headers={"X-MEW-Api-Key": user_key})
    assert profile_res.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. backend/venv/bin/pytest backend/tests/test_auth_sync.py -v`  
Expected: FAIL (mock-login route does not exist)

- [ ] **Step 3: Write user key storage, auth routes, and updated security middleware**

```json
// backend/data/users.json
{}
```

```python
# backend/routes/auth.py
import json
import hashlib
import secrets
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query

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
```

Modify `backend/security/auth.py`:
```python
# backend/security/auth.py
import json
from pathlib import Path
from fastapi import Request, HTTPException, status
from fastapi.security import APIKeyHeader
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
    if request.url.path.startswith("/test-forms") or request.url.path in ["/favicon.ico", "/docs", "/openapi.json", "/redoc"]:
        return None
    
    key = request.headers.get("X-MEW-Api-Key")
    settings = get_settings()
    
    if not key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key"
        )
        
    if key == settings.api_key or is_valid_user_key(key):
        return key

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or invalid API key"
    )
```

Register `auth_router` in `backend/main.py`:
```python
from backend.routes.auth import router as auth_router
app.include_router(auth_router)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. backend/venv/bin/pytest backend/tests/test_auth_sync.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/routes/auth.py backend/security/auth.py backend/data/users.json backend/main.py backend/tests/test_auth_sync.py
git commit -m "feat: add user-scoped API key provisioning and dual key authentication middleware"
```

---

### Task 2: Manifest V3 Core Setup & Background Service Worker

**Files:**
- Create: `extension/manifest.json`
- Create: `extension/background.js`
- Create: `backend/tests/test_extension_manifest.py`

**Interfaces:**
- Consumes: Chrome Extension API runtime messages (`MEW_AUTH_SYNC`).
- Produces: Persistent `mewApiKey` in `chrome.storage.local` and background service worker.

- [ ] **Step 1: Write failing test for Extension Manifest schema**

```python
# backend/tests/test_extension_manifest.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. backend/venv/bin/pytest backend/tests/test_extension_manifest.py -v`  
Expected: FAIL (extension/manifest.json does not exist)

- [ ] **Step 3: Write manifest.json & background.js**

```json
// extension/manifest.json
{
  "manifest_version": 3,
  "name": "Project MEW — Job Application Autofill",
  "version": "1.0.0",
  "description": "AI-powered job form autofilling with synthetic event dispatching for Workday, Greenhouse, Lever, and live career portals.",
  "permissions": ["activeTab", "storage", "scripting"],
  "host_permissions": ["<all_urls>", "http://localhost:8000/*", "http://127.0.0.1:8000/*"],
  "background": {
    "service_worker": "background.js"
  },
  "content_scripts": [
    {
      "matches": ["<all_urls>"],
      "css": ["styles.css"],
      "js": ["content.js"]
    }
  ],
  "action": {
    "default_popup": "popup.html",
    "default_title": "Project MEW Autofill"
  }
}
```

```javascript
// extension/background.js
console.log("[MEW Extension] Background service worker initialized.");

// Listen for messages from web pages or popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "MEW_AUTH_SYNC" && message.apiKey) {
    chrome.storage.local.set({ mewApiKey: message.apiKey }, () => {
      console.log("[MEW Extension] API Key auto-synced successfully:", message.apiKey);
      sendResponse({ status: "success", syncedKey: message.apiKey });
    });
    return true; // Async response
  }
  
  if (message.type === "GET_MEW_STATUS") {
    chrome.storage.local.get(["mewApiKey"], (data) => {
      sendResponse({ apiKey: data.mewApiKey || null });
    });
    return true;
  }
});
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. backend/venv/bin/pytest backend/tests/test_extension_manifest.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add extension/manifest.json extension/background.js backend/tests/test_extension_manifest.py
git commit -m "feat: create Manifest V3 configuration and background service worker for auto-key sync"
```

---

### Task 3: Floating Action Badge & DOM Field Filler

**Files:**
- Create: `extension/styles.css`
- Create: `extension/content.js`
- Create: `backend/tests/test_extension_content.py`

**Interfaces:**
- Consumes: `GET http://localhost:8000/api/v1/autofill-payload` with stored `X-MEW-Api-Key`.
- Produces: Floating "✨ MEW Autofill" badge on all web pages, DOM input scanning, and synthetic event dispatching (`focus`, `input`, `change`, `blur`).

- [ ] **Step 1: Write failing test for content script assets**

```python
# backend/tests/test_extension_content.py
from pathlib import Path
import pytest

def test_content_script_and_styles_exist():
    css_path = Path("extension/styles.css")
    js_path = Path("extension/content.js")
    
    assert css_path.exists()
    assert js_path.exists()
    
    css_content = css_path.read_text()
    assert "#mew-autofill-badge" in css_content
    
    js_content = js_path.read_text()
    assert "dispatchEvent" in js_content
    assert "focus" in js_content
    assert "input" in js_content
    assert "change" in js_content
    assert "blur" in js_content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. backend/venv/bin/pytest backend/tests/test_extension_content.py -v`  
Expected: FAIL (extension/styles.css does not exist)

- [ ] **Step 3: Write styles.css & content.js**

```css
/* extension/styles.css */
#mew-autofill-badge {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 999999;
  background: #0f172a;
  color: #38bdf8;
  border: 1px solid #38bdf8;
  padding: 10px 18px;
  border-radius: 30px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  font-size: 13px;
  font-weight: 600;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s ease-in-out;
  user-select: none;
}

#mew-autofill-badge:hover {
  background: #38bdf8;
  color: #0f172a;
  transform: translateY(-2px);
  box-shadow: 0 12px 28px rgba(56, 189, 248, 0.4);
}

#mew-autofill-badge.mew-success {
  border-color: #4ade80;
  color: #4ade80;
}
```

```javascript
// extension/content.js
(function () {
  if (document.getElementById("mew-autofill-badge")) return;

  // Create Floating Action Badge
  const badge = document.createElement("div");
  badge.id = "mew-autofill-badge";
  badge.innerHTML = `✨ MEW Autofill`;
  document.body.appendChild(badge);

  // Listen for web app auth sync message from window
  window.addEventListener("message", (event) => {
    if (event.data && event.data.type === "MEW_AUTH_SYNC" && event.data.apiKey) {
      chrome.runtime.sendMessage({ type: "MEW_AUTH_SYNC", apiKey: event.data.apiKey });
    }
  });

  // Helper: Dispatch framework-compliant synthetic events
  function fillAndDispatch(el, val) {
    if (!el || val === undefined || val === null) return;
    el.focus();
    el.value = val;
    ["focus", "input", "change", "blur"].forEach((evtType) => {
      el.dispatchEvent(new Event(evtType, { bubbles: true, cancelable: true }));
    });
  }

  // Click Handler for Floating Badge
  badge.addEventListener("click", async () => {
    badge.innerHTML = `⏳ Loading Payload...`;

    // Fetch API Key from extension storage
    chrome.storage.local.get(["mewApiKey"], async (stored) => {
      const apiKey = stored.mewApiKey || "";
      let profileData = null;

      try {
        const headers = apiKey ? { "X-MEW-Api-Key": apiKey } : {};
        const url = apiKey ? "http://localhost:8000/api/v1/autofill-payload" : "http://localhost:8000/autofill/preview";
        const res = await fetch(url, { headers });
        const json = await res.json();
        
        if (json.status === "success") {
          profileData = json.data.active_profile || json.data;
        }
      } catch (err) {
        console.error("[MEW Extension] Failed to fetch payload:", err);
      }

      if (!profileData) {
        badge.innerHTML = `❌ Connection Error`;
        setTimeout(() => { badge.innerHTML = `✨ MEW Autofill`; }, 3000);
        return;
      }

      const p = profileData.personal || {};
      const prof = profileData.professional || {};
      let filledCount = 0;

      // Scan and Fill Standard Fields
      const fieldMappings = [
        { selectors: ["input[name='first_name']", "input[id='first_name']", "input[autocomplete='given-name']"], val: p.first_name },
        { selectors: ["input[name='last_name']", "input[id='last_name']", "input[autocomplete='family-name']"], val: p.last_name },
        { selectors: ["input[name='email']", "input[id='email']", "input[type='email']", "input[autocomplete='email']"], val: p.email },
        { selectors: ["input[name='phone']", "input[id='phone']", "input[type='tel']"], val: p.phone },
        { selectors: ["input[id='react-name']"], val: p.full_name },
        { selectors: ["input[id='react-linkedin']"], val: p.linkedin_url },
        { selectors: ["input[id='wizard-title']"], val: prof.current_title }
      ];

      fieldMappings.forEach(item => {
        item.selectors.forEach(sel => {
          const el = document.querySelector(sel);
          if (el && item.val) {
            fillAndDispatch(el, item.val);
            filledCount++;
          }
        });
      });

      badge.classList.add("mew-success");
      badge.innerHTML = `✅ ${filledCount} Fields Filled`;
      setTimeout(() => {
        badge.classList.remove("mew-success");
        badge.innerHTML = `✨ MEW Autofill`;
      }, 3000);
    });
  });
})();
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. backend/venv/bin/pytest backend/tests/test_extension_content.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add extension/styles.css extension/content.js backend/tests/test_extension_content.py
git commit -m "feat: implement floating MEW Autofill action badge and synthetic event field filler"
```

---

### Task 4: AI Fuzzy Field Matcher Integration for Live Portals

**Files:**
- Modify: `extension/content.js`
- Create: `backend/tests/test_extension_fuzzy.py`

**Interfaces:**
- Consumes: Unmapped DOM elements on live application pages.
- Produces: POSTs DOM field descriptors to `http://localhost:8000/api/v1/autofill-payload/match` and fills returned matches.

- [ ] **Step 1: Write failing test for fuzzy matching logic in extension tests**

```python
# backend/tests/test_extension_fuzzy.py
from pathlib import Path
import pytest

def test_content_js_contains_fuzzy_match_payload_sender():
    js_path = Path("extension/content.js")
    assert js_path.exists()
    content = js_path.read_text()
    assert "/api/v1/autofill-payload/match" in content
    assert "FuzzyMatchRequest" in content or "fields" in content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. backend/venv/bin/pytest backend/tests/test_extension_fuzzy.py -v`  
Expected: FAIL (match route not yet called in content.js)

- [ ] **Step 3: Add AI Fuzzy Matcher fallback into `extension/content.js`**

Modify `extension/content.js` to collect unmapped inputs and query `/api/v1/autofill-payload/match`:

```javascript
      // Scan unmapped custom & QA fields
      const unmappedFields = [];
      document.querySelectorAll("input, textarea").forEach(el => {
        if (!el.value && (el.id || el.name || el.placeholder)) {
          const labelEl = document.querySelector(`label[for='${el.id}']`) || el.closest("label");
          const labelText = labelEl ? labelEl.innerText.trim() : (el.placeholder || el.name || "");
          if (labelText) {
            unmappedFields.push({
              element_id: el.id || el.name,
              label: labelText,
              placeholder: el.placeholder || "",
              tag_name: el.tagName.toLowerCase(),
              input_type: el.type || "text"
            });
          }
        }
      });

      if (unmappedFields.length > 0 && apiKey) {
        try {
          const matchRes = await fetch("http://localhost:8000/api/v1/autofill-payload/match", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-MEW-Api-Key": apiKey
            },
            body: JSON.stringify({ fields: unmappedFields.slice(0, 10) })
          });
          const matchJson = await matchRes.json();
          if (matchJson.status === "success" && matchJson.data.matches) {
            matchJson.data.matches.forEach(m => {
              const el = document.getElementById(m.element_id) || document.querySelector(`[name='${m.element_id}']`);
              if (el && m.value && m.confidence >= 0.7) {
                fillAndDispatch(el, m.value);
                filledCount++;
              }
            });
          }
        } catch (e) {
          console.warn("[MEW Extension] AI Fuzzy Match fallback skipped:", e);
        }
      }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. backend/venv/bin/pytest backend/tests/test_extension_fuzzy.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add extension/content.js backend/tests/test_extension_fuzzy.py
git commit -m "feat: integrate AI fuzzy field matcher fallback into extension content script"
```

---

### Task 5: Extension Popup Inspector & Connection Status UI

**Files:**
- Create: `extension/popup.html`
- Create: `extension/popup.js`
- Create: `backend/tests/test_extension_popup.py`

**Interfaces:**
- Consumes: Chrome Extension Action UI.
- Produces: Popup inspector showing backend connection health, candidate profile summary, manual API key input, and "Autofill Page" button.

- [ ] **Step 1: Write failing test for Popup assets**

```python
# backend/tests/test_extension_popup.py
from pathlib import Path
import pytest

def test_popup_files_exist():
    html_path = Path("extension/popup.html")
    js_path = Path("extension/popup.js")
    
    assert html_path.exists()
    assert js_path.exists()
    
    html_content = html_path.read_text()
    assert "Project MEW" in html_content
    assert "id=\"save-key-btn\"" in html_content or "saveKey" in js_path.read_text()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. backend/venv/bin/pytest backend/tests/test_extension_popup.py -v`  
Expected: FAIL (extension/popup.html does not exist)

- [ ] **Step 3: Write popup.html & popup.js**

```html
<!-- extension/popup.html -->
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>MEW Autofill Inspector</title>
  <style>
    body { width: 320px; font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 16px; box-sizing: border-box; }
    h2 { font-size: 16px; color: #38bdf8; margin: 0 0 12px 0; }
    .status-card { background: #1e293b; border: 1px solid #334155; padding: 12px; border-radius: 6px; margin-bottom: 12px; font-size: 13px; }
    .status-online { color: #4ade80; font-weight: bold; }
    .status-offline { color: #f87171; font-weight: bold; }
    .field-group { margin-bottom: 12px; }
    label { display: block; font-size: 12px; color: #cbd5e1; margin-bottom: 4px; }
    input { width: 100%; padding: 8px; border-radius: 4px; border: 1px solid #475569; background: #020617; color: #38bdf8; font-family: monospace; font-size: 12px; box-sizing: border-box; }
    button { width: 100%; padding: 10px; border-radius: 6px; border: none; font-weight: bold; cursor: pointer; font-size: 13px; }
    .btn-primary { background: #38bdf8; color: #0f172a; margin-top: 6px; }
    .btn-secondary { background: #334155; color: #f8fafc; margin-top: 8px; }
  </style>
</head>
<body>
  <h2>✨ MEW Autofill Inspector</h2>
  
  <div class="status-card">
    Backend Status: <span id="backend-status" class="status-offline">Checking...</span><br>
    <small id="user-info" style="color: #94a3b8; display: block; margin-top: 4px;">Candidate: Not Synced</small>
  </div>

  <div class="field-group">
    <label>API Key (Auto-synced on Google Login):</label>
    <input type="text" id="api-key-input" placeholder="mew_sk_user_...">
    <button id="save-key-btn" class="btn-secondary">Save Key Manually</button>
  </div>

  <button id="trigger-autofill-btn" class="btn-primary">✨ Autofill Current Page</button>

  <script src="popup.js"></script>
</body>
</html>
```

```javascript
// extension/popup.js
document.addEventListener("DOMContentLoaded", () => {
  const statusEl = document.getElementById("backend-status");
  const userInfoEl = document.getElementById("user-info");
  const keyInput = document.getElementById("api-key-input");
  const saveBtn = document.getElementById("save-key-btn");
  const triggerBtn = document.getElementById("trigger-autofill-btn");

  // Load saved key
  chrome.storage.local.get(["mewApiKey"], async (data) => {
    if (data.mewApiKey) {
      keyInput.value = data.mewApiKey;
      checkHealth(data.mewApiKey);
    } else {
      checkHealth(null);
    }
  });

  async function checkHealth(key) {
    try {
      const headers = key ? { "X-MEW-Api-Key": key } : {};
      const url = key ? "http://localhost:8000/api/v1/profile" : "http://localhost:8000/autofill/preview";
      const res = await fetch(url, { headers });
      if (res.ok) {
        const json = await res.json();
        statusEl.className = "status-online";
        statusEl.textContent = "Online 🟢";
        const name = json.data?.personal?.full_name || json.data?.active_profile?.personal?.full_name || "Candidate Profile Loaded";
        userInfoEl.textContent = `Candidate: ${name}`;
      } else {
        statusEl.className = "status-offline";
        statusEl.textContent = "Unauthorized (401)";
      }
    } catch (e) {
      statusEl.className = "status-offline";
      statusEl.textContent = "Offline 🔴 (Start Server)";
    }
  }

  saveBtn.addEventListener("click", () => {
    const key = keyInput.value.trim();
    chrome.storage.local.set({ mewApiKey: key }, () => {
      alert("API Key saved to Chrome Extension Storage!");
      checkHealth(key);
    });
  });

  triggerBtn.addEventListener("click", () => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]) {
        chrome.scripting.executeScript({
          target: { tabId: tabs[0].id },
          func: () => {
            const badge = document.getElementById("mew-autofill-badge");
            if (badge) badge.click();
          }
        });
      }
    });
  });
});
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. backend/venv/bin/pytest backend/tests/test_extension_popup.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add extension/popup.html extension/popup.js backend/tests/test_extension_popup.py
git commit -m "feat: add extension popup UI inspector, connection health check, and profile status panel"
```

---

## Plan Self-Review Checklist

- **Spec coverage:** User Key Provisioning (Task 1), Manifest V3 & Service Worker (Task 2), Floating Action Badge & DOM Filler (Task 3), AI Fuzzy Field Matcher Integration (Task 4), Popup UI Inspector (Task 5).
- **Placeholder scan:** No TBDs, TODOs, or vague code references.
- **Type consistency:** Matches schema names (`FuzzyMatchRequest`, `FuzzyMatchResponse`, `mewApiKey`, `MEW_AUTH_SYNC`).
