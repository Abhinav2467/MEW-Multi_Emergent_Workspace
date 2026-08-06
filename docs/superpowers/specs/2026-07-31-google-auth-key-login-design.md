# Design Specification: Google Access Key Auth & Navigation Lock

**Date**: 2026-07-31  
**Status**: Approved  

---

## 1. Overview
This specification updates the Landing Page authentication UI in `claude_frontend/landing.html/index.html` to replace the email/password login with the Google Access Key & Private Code setup, and enforces strict navigation locking until authentication is completed.

---

## 2. Updated Auth UI & Workflow

### 1. Landing Page Auth Card Changes
* **Removed Elements**: Work Email input and Password input.
* **New Auth Layout**:
  1. **"Get Google Access Key" Button**:
     * Triggers `window.open('/auth/google', '_blank')` (or `http://localhost:8000/auth/google`) to open Google OAuth authorization in a new browser tab.
  2. **Private Access Key Input Box**:
     * Input field: `<input id="auth-private-key" placeholder="Paste Google Authorization Code (e.g. 4/1AXEQ...)" type="text" />`
  3. **"Login & Verify" Button**:
     * Submits the entered private key / authorization code to backend endpoint `GET /auth/callback?code=<KEY>` (or authenticates token).
     * On successful verification:
       * Stores `access_token` in `localStorage`.
       * Sets `window.MewAppState.user.isAuthenticated = true`.
       * Unlocks navigation to Resume Parser & AI Job Matcher views.
       * Transitions seamlessly to `#view-parser`.

---

## 3. Navigation Lock & Auth Guard

* **Unauthenticated State**:
  * Initial state: `window.MewAppState.user.isAuthenticated = false`.
  * Attempting to click sidebar links (`Resume Parser`, `Job Matches`, `Dashboard`) or top header stepper steps (`2. Resume Parser`, `3. AI Matches`) will **block navigation**.
  * Shows a visual warning toast on the Auth card: **"Authentication Required: Please enter your Google Access Key to proceed."**
  * Stepper icons display lock icons ($🔒$) for step 2 & step 3 until authenticated.

* **Authenticated State**:
  * Stepper step 1 updates to checkmark ($✓$).
  * Resume Parser and Job Matcher pages become fully interactive and accessible.

---

## 4. Backend AI Workflow Connection
* Ensures real backend endpoints (`http://localhost:8000`) handle:
  * Google OAuth URL generation (`/auth/google`) & Code exchange (`/auth/callback`).
  * PDF/DOCX Resume upload & Gemini Flash skill extraction (`/upload-resume`).
  * AI Job Search Agent confirmation & card scoring (`/resume/{id}/confirm`).
  * Recruiter discovery & Gmail cold email drafting (`/emails/drafts`, `/emails/send`).

---

## 5. Verification Plan
* Test clicking "Get Google Access Key" opens a new tab.
* Test entering an authorization code and clicking "Login & Verify" unlocks the application and switches to Resume Parser.
* Test that clicking sidebar links or stepper steps while unauthenticated is strictly blocked.
