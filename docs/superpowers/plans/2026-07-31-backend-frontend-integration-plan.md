# Backend-Frontend Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect the unified Single-Page Web Application (`claude_frontend/landing.html/index.html`) with the FastAPI backend API (`http://localhost:8000`), adding recruiter email outreach elements, report downloads, real file parsing, and backend status detection with local fallback.

**Architecture:** A client-side API engine (`MewApiClient`) built into `index.html` that interfaces with FastAPI routes (`/auth/google`, `/upload-resume`, `/resume/{id}/confirm`, `/jobs`, `/emails/drafts`, `/emails/send`, `/reports/{id}/excel`). Includes health checking, JWT session storage, and an automatic fallback mode for offline testing.

**Tech Stack:** HTML5, Vanilla JS (Fetch API, FormData), Tailwind CSS, FastAPI backend (`http://localhost:8000`).

## Global Constraints
- Target file: `claude_frontend/landing.html/index.html`
- Base URL: `http://localhost:8000`
- Seamless fallback: Must work cleanly both when backend is running AND when backend is offline.

---

### Task 1: Build API Service Layer (`MewApiClient`) & Health Detection

**Files:**
- Modify: `claude_frontend/landing.html/index.html`

**Interfaces:**
- Consumes: `http://localhost:8000/health`, `/auth/me`
- Produces: `window.MewApiClient` module with `checkHealth()`, `getAuthUrl()`, `uploadResume(file)`, `confirmProfile(id, profile)`, `getJobs(reportId)`, `createDrafts(matchIds)`, `sendEmail(draftIds)`, and `getExcelUrl(reportId)`.

- [ ] **Step 1: Add `MewApiClient` class to `index.html` script block with fetch wrappers and error handling**
- [ ] **Step 2: Add backend health status check (`/health`) on application load**
- [ ] **Step 3: Update sidebar UI badge (`🟢 Backend Connected` vs `🟡 Demo Mode`)**
- [ ] **Step 4: Commit API service layer**

```bash
git add claude_frontend/landing.html/index.html
git commit -m "feat: add MewApiClient service layer and backend health status indicator"
```

---

### Task 2: Connect Authentication Routes (`/auth/*`)

**Files:**
- Modify: `claude_frontend/landing.html/index.html`

**Interfaces:**
- Consumes: `MewApiClient.getAuthUrl()`, `handleGoogleAuth()`, `handleAuthSubmit()`
- Produces: Google OAuth redirect and JWT token persistence in `localStorage`.

- [ ] **Step 1: Wire `Continue with Google` button to call backend `/auth/google` route**
- [ ] **Step 2: Add OAuth callback handler (`?code=...`) to store JWT `access_token`**
- [ ] **Step 3: Sync user state with `/auth/me` endpoint when token is present**
- [ ] **Step 4: Commit auth route integration**

```bash
git add claude_frontend/landing.html/index.html
git commit -m "feat: connect Google OAuth and JWT auth handlers with backend"
```

---

### Task 3: Connect Resume Upload & Confirmation Routes (`/upload-resume`, `/resume/{id}/confirm`)

**Files:**
- Modify: `claude_frontend/landing.html/index.html`

**Interfaces:**
- Consumes: `MewApiClient.uploadResume()`, `MewApiClient.confirmProfile()`
- Produces: Real file parsing with Gemini Flash backend, populating profile fields and returning matched jobs on confirmation.

- [ ] **Step 1: Update `handleFileSelect()` and Drag & Drop handler to call `POST /upload-resume` with `FormData`**
- [ ] **Step 2: Populate extracted profile fields (Contact info, Core skills, Experience) from backend response**
- [ ] **Step 3: Update `saveResumeAndGoToMatches()` to call `POST /resume/{id}/confirm`**
- [ ] **Step 4: Commit resume API integration**

```bash
git add claude_frontend/landing.html/index.html
git commit -m "feat: connect resume upload and profile confirmation endpoints to backend"
```

---

### Task 4: Add Recruiter Outreach & Excel Export Elements to Job Matcher

**Files:**
- Modify: `claude_frontend/landing.html/index.html`

**Interfaces:**
- Consumes: `/jobs`, `/emails/drafts`, `/emails/send`, `/reports/{id}/excel`
- Produces: Recruiter detail badges on job cards, "Create Email Draft", "Send Outreach", and "Download Excel Report" buttons.

- [ ] **Step 1: Add HR Recruiter Name & Email badges to job match cards**
- [ ] **Step 2: Add "Create Recruiter Email Draft" (`POST /emails/drafts`) button to job cards**
- [ ] **Step 3: Add "Send Cold Outreach" (`POST /emails/send`) action handler with modal feedback**
- [ ] **Step 4: Add "Download Excel Report" button in Job Matcher header calling `/reports/{id}/excel`**
- [ ] **Step 5: Commit recruiter outreach and report export UI elements**

```bash
git add claude_frontend/landing.html/index.html
git commit -m "feat: add recruiter email outreach agent controls and Excel export to Job Matcher"
```

---

### Task 5: End-to-End Verification & Testing

**Files:**
- Verify: `claude_frontend/landing.html/index.html`

- [ ] **Step 1: Verify offline demo fallback mode works cleanly without backend running**
- [ ] **Step 2: Test backend connection when FastAPI backend is active on `http://localhost:8000`**
- [ ] **Step 3: Commit final integrated codebase**

```bash
git add claude_frontend/landing.html/index.html
git commit -m "chore: verify complete backend-frontend integration"
```
