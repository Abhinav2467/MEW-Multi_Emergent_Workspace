# Landing Sidebar Hiding, Resume Parser & Extension Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hide the sidebar on the Landing Page view, link the Resume Parser workspace to real Gemini Flash PDF parsing (`/api/v1/parse-resume`), and add `/api/v1/sync-profile` to save & sync candidate edits directly to `profile.json` for the Chrome Extension.

**Architecture:** Update `MewRouter.navigateTo()` in `index.html` to toggle sidebar visibility per view, add `/api/v1/sync-profile` route in `backend/api/routes/autofill.py`, and wire `simulateParsing()` and `saveResumeAndGoToMatches()` to backend endpoints.

**Tech Stack:** HTML5, Vanilla JS, Tailwind CSS, FastAPI backend (`http://localhost:8000`), `autofill_agent/backend/data/profile.json`.

## Global Constraints
- Target files: `claude_frontend/landing.html/index.html`, `backend/api/routes/autofill.py`
- Do NOT use git commit or git push (user directive).
- Landing page must render full width without sidebar.
- Chrome Extension sync writes to `profile.json`.

---

### Task 1: Add `/api/v1/sync-profile` Endpoint in Backend

**Files:**
- Modify: `backend/api/routes/autofill.py`

**Interfaces:**
- Consumes: `POST /api/v1/sync-profile` with `{ personal: { full_name, email, phone, location }, professional: { current_title, primary_skills } }`
- Produces: Updates `autofill_agent/backend/data/profile.json` using `sync_profile_to_autofill_json()`.

- [ ] **Step 1: Add `SyncProfileRequest` schema and `POST /api/v1/sync-profile` route in `backend/api/routes/autofill.py`**
- [ ] **Step 2: Verify `profile.json` is updated when called**

---

### Task 2: Hide Sidebar on Landing Page View in `index.html`

**Files:**
- Modify: `claude_frontend/landing.html/index.html`

**Interfaces:**
- Consumes: `MewRouter.navigateTo(viewName)`
- Produces: Sidebar `<aside>` hidden (`display: none`) and main container padding set to `pl-0` when `viewName === 'landing'`, showing sidebar and `pl-72` for other views.

- [ ] **Step 1: Update `MewRouter.navigateTo(viewName)` to toggle `<aside>` element visibility**
- [ ] **Step 2: Toggle main wrapper padding (`pl-0` vs `pl-72`) and top header left offset (`left-0` vs `left-72`)**

---

### Task 3: Link Resume Parser & Chrome Extension Sync in `index.html`

**Files:**
- Modify: `claude_frontend/landing.html/index.html`

**Interfaces:**
- Consumes: `/api/v1/parse-resume`, `/api/v1/sync-profile`
- Produces: Real PDF/DOCX parsing populating DOM fields, and "Save to Matches" syncing to `profile.json`.

- [ ] **Step 1: Update `simulateParsing(filename, fileObj)` to post `fileObj` to `/api/v1/parse-resume`**
- [ ] **Step 2: Populate extracted `full_name`, `email`, `phone`, `location`, `skills`, `current_title` in editor**
- [ ] **Step 3: Update `saveResumeAndGoToMatches()` to call `/api/v1/sync-profile`**
- [ ] **Step 4: Display toast notification: "Profile saved & synced with Chrome Extension"**

---

### Task 4: End-to-End Verification

**Files:**
- Verify: `claude_frontend/landing.html/index.html`

- [ ] **Step 1: Verify landing page renders full width with no sidebar**
- [ ] **Step 2: Upload PDF resume and verify real Gemini Flash fields populate on Parser page**
- [ ] **Step 3: Click "Save to Matches" and verify `autofill_agent/backend/data/profile.json` is updated**
