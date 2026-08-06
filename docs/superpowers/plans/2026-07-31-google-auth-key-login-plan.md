# Google Access Key Auth & Navigation Lock Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace email/password login in `index.html` with the "Get Google Access Key" button and Private Access Key input box, and strictly lock navigation to Resume Parser / AI Job Matcher until authentication is complete.

**Architecture:** Update `claude_frontend/landing.html/index.html` auth card UI, integrate `window.open(url, '_blank')` for Google Auth, connect private key verification with `/auth/callback?code=...`, and add navigation guard in `MewRouter.navigateTo()` checking `MewAppState.user.isAuthenticated`.

**Tech Stack:** HTML5, Vanilla JS ES6+, Tailwind CSS, FastAPI backend (`http://localhost:8000`).

## Global Constraints
- Target file: `claude_frontend/landing.html/index.html`
- Do NOT use git commit or git push (user directive).
- Email & password fields removed completely.
- Navigation to Resume Parser, Job Matcher, and Dashboard strictly blocked until authenticated.

---

### Task 1: Update Auth Card UI in `index.html`

**Files:**
- Modify: `claude_frontend/landing.html/index.html`

**Interfaces:**
- Consumes: `landing` view container
- Produces: Updated auth form with "Get Google Access Key" button, Private Access Key input `#auth-private-key`, and "Login & Verify" button `#btn-login-verify`.

- [ ] **Step 1: Remove Email and Password input fields from `#auth-form` in `index.html`**
- [ ] **Step 2: Add "Get Google Access Key" button calling `openGoogleAuthWindow()`**
- [ ] **Step 3: Add Private Access Key label & input box `#auth-private-key`**
- [ ] **Step 4: Add "Login & Verify" submit button calling `handleKeyLoginSubmit()`**

---

### Task 2: Implement Key Verification & OAuth Flow

**Files:**
- Modify: `claude_frontend/landing.html/index.html`

**Interfaces:**
- Consumes: `MewApiClient.getAuthUrl()`, `http://localhost:8000/auth/callback`
- Produces: `openGoogleAuthWindow()` opening OAuth in a new tab, `handleKeyLoginSubmit()` validating private key, saving token, setting `isAuthenticated = true`, and advancing to Parser view.

- [ ] **Step 1: Implement `openGoogleAuthWindow()` to fetch auth URL and open `window.open(url, '_blank')`**
- [ ] **Step 2: Implement `handleKeyLoginSubmit()` to send key to `/auth/callback?code=<KEY>`**
- [ ] **Step 3: Save `access_token` into `localStorage` and set `MewAppState.user.isAuthenticated = true`**

---

### Task 3: Implement Navigation Guard & Page Locking

**Files:**
- Modify: `claude_frontend/landing.html/index.html`

**Interfaces:**
- Consumes: `MewRouter.navigateTo(viewName)`
- Produces: Navigation check blocking unauthenticated access to `parser`, `matches`, and `dashboard`.

- [ ] **Step 1: Add authentication check inside `MewRouter.navigateTo(viewName)`**
- [ ] **Step 2: Block navigation to non-landing views when `!MewAppState.user.isAuthenticated`**
- [ ] **Step 3: Display "Authentication Required" toast message when blocked**
- [ ] **Step 4: Update header stepper icons ($🔒$ vs $✓$) based on authentication state**

---

### Task 4: End-to-End Verification

**Files:**
- Verify: `claude_frontend/landing.html/index.html`

- [ ] **Step 1: Verify clicking "Get Google Access Key" opens Google OAuth in a new tab**
- [ ] **Step 2: Verify entering key and clicking "Login & Verify" unlocks app and navigates to Parser**
- [ ] **Step 3: Verify sidebar and stepper navigation is locked until authenticated**
