# Project MEW — Google Auth Auto-Sync & Live Career Portal Extension Design

**Date:** 2026-07-28  
**Author:** AI Pair Programmer & Lead Developer  
**Status:** Approved  

---

## 1. Overview & Objectives

This design specifies the architecture for:
1. **Google OAuth & Unique Key Auto-Sync:** Allowing candidates to log in via Google Auth on the MEW Web Dashboard, which automatically provisions a unique API key and syncs it to their Chrome Extension via native messaging—completely eliminating manual key copy-pasting.
2. **Live Career Portal Manifest V3 Extension (`extension/`):** A production-ready Chrome Extension capable of running on ANY live career application site (Workday, Greenhouse, Lever, LinkedIn, Ashby, SmartRecruiters, custom career forms). It injects a floating **"✨ MEW Autofill"** badge, fetches the candidate payload from `http://localhost:8000`, maps standard + custom QA fields, and dispatches framework synthetic events.

---

## 2. Directory Layout & Components

```text
development/mew/
├── backend/
│   ├── routes/
│   │   ├── auth.py                 # Google OAuth login & unique user key provisioning
│   │   └── autofill.py             # User-scoped payload delivery & AI fuzzy field matcher
│   ├── security/
│   │   └── auth.py                 # Key validation supporting both global & unique user keys
│   └── data/
│       ├── users.json              # Storage for unique Google user accounts & API keys
│       └── profile.json            # Active candidate profile
├── extension/
│   ├── manifest.json               # Manifest V3 configuration (<all_urls>, background service worker)
│   ├── background.js               # Service worker listening for auth sync & extension storage
│   ├── content.js                  # Injected script: Floating "✨ MEW Autofill" badge & DOM filling
│   ├── styles.css                  # Floating badge glassmorphism styling
│   ├── popup.html                  # Extension status panel & profile inspector
│   └── popup.js                    # Extension popup logic & manual trigger
└── docs/
    └── superpowers/specs/2026-07-28-mew-live-extension-auth-sync-design.md
```

---

## 3. Google Auth & Auto-Key Sync Architecture

### 3.1 Backend Unique User Provisioning (`backend/routes/auth.py`)
- **`GET /api/v1/auth/google/login`**: Redirects user to Google OAuth consent.
- **`GET /api/v1/auth/callback`**: Exchanges code for Google user profile (`sub`, `email`, `name`).
- Generates or retrieves a unique user API key formatted as `mew_sk_user_<sub_hash>`.
- Stores user mapping in `backend/data/users.json`.
- Returns `{ "status": "success", "user": { "email": "...", "api_key": "mew_sk_user_..." } }`.

### 3.2 Key Validation (`backend/security/auth.py`)
- Checks `X-MEW-Api-Key` header against global key in `.env` OR any active user key registered in `backend/data/users.json`.

### 3.3 Seamless Extension Auto-Sync (`extension/background.js` & `extension/content.js`)
- When the candidate logs in on the MEW Web Dashboard (`http://localhost:8000` or web domain), the page dispatches:
  ```javascript
  window.postMessage({ type: "MEW_AUTH_SYNC", apiKey: "mew_sk_user_..." }, "*");
  ```
- The extension content script catches `MEW_AUTH_SYNC` and sends it to `background.js`:
  ```javascript
  chrome.storage.local.set({ mewApiKey: event.data.apiKey });
  ```
- Result: As soon as the user logs in on the website, their Chrome Extension is automatically authenticated!

---

## 4. Live Career Portal Extension Specification (`extension/`)

### 4.1 Manifest V3 (`extension/manifest.json`)
```json
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

### 4.2 Floating Action Badge ("✨ MEW Autofill")
- Injected automatically into the bottom-right corner (`position: fixed; bottom: 20px; right: 20px; z-index: 999999;`).
- Sleek glassmorphism UI: Dark background `#0f172a`, cyan border `#38bdf8`, hover animation.
- Clicking the badge triggers full page autofill.

### 4.3 DOM Scanning & Event Dispatching (`extension/content.js`)
1. Reads `mewApiKey` from `chrome.storage.local`. If absent, prompts user or falls back to public test preview endpoint.
2. Fetches payload from `http://localhost:8000/api/v1/autofill-payload`.
3. Scans form elements:
   - Maps standard field types (`given-name`, `family-name`, `email`, `tel`, `url`, `first_name`, `last_name`, `phone`, `linkedin`, `github`).
   - Identifies custom/unlabelled fields and sends DOM descriptors to `POST /api/v1/autofill-payload/match` for AI fuzzy matching.
4. For every matched element:
   ```javascript
   element.focus();
   element.value = val;
   ['focus', 'input', 'change', 'blur'].forEach(evt => {
     element.dispatchEvent(new Event(evt, { bubbles: true, cancelable: true }));
   });
   ```
5. Displays a visual success indicator on the badge ("✅ 6 Fields Autofilled").

---

## 5. Verification Plan

### 5.1 Extension Load Verification
- Load `extension/` directory into Chrome via `chrome://extensions` -> "Load unpacked".
- Verify extension popup displays connection status to `http://localhost:8000`.

### 5.2 Live Portal Verification
- Open live career application URLs in Google Chrome:
  - Scenario A: Workday Application Page.
  - Scenario B: Greenhouse Job Board (`boards.greenhouse.io`).
  - Scenario C: Lever Application Page (`jobs.lever.co`).
  - Scenario D: Local Test Runner (`http://localhost:8000/test-forms`).
- Confirm floating "✨ MEW Autofill" badge appears in bottom-right corner.
- Click badge and verify all form fields populate and dispatches input/change events correctly.
