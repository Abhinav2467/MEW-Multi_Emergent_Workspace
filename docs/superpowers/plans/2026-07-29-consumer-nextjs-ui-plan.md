# AI Cold Email Drafting Engine & Gmail OAuth Send Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a complete AI Cold Email Drafting Engine in `JobExplorer.jsx`, dual action buttons per job card (`[Autofill]` and `[Draft AI Cold Email]`), animated drafting state, editable email studio, HR Recruiter verification modal popup, direct Gmail OAuth email dispatching, and Chrome extension live profile sync.

**Architecture:** Add `POST /api/v1/emails/generate` and `POST /api/v1/emails/send` routes in `backend/api/routes/emails.py`. Build `EmailStudio.jsx` and `HrVerificationModal.jsx` in frontend. Update Chrome extension `content.js` to fetch live profile data from `/api/v1/profile`.

**Tech Stack:** Next.js, React 19, FastAPI, Gemini AI LLM, Gmail API, SQLite.

## Global Constraints
- Every job card has two buttons: `[⚡ Autofill Application]` and `[✉️ Draft AI Cold Email]`.
- Clicking `[✉️ Draft AI Cold Email]` shows a drafting animation and renders the Cyber Email Editor below job cards.
- Email Editor contains `[🔄 Regenerate Email]` and `[🚀 Send Email via Gmail OAuth]`.
- Clicking `[🚀 Send Email via Gmail OAuth]` opens HR Verification Modal with editable HR email input and confirmation button.
- Extension `content.js` fetches `/api/v1/profile` directly so profile updates are live immediately.

---

### Task 1: Extension Plugin Live Profile Fetch & Backend Email Endpoints

**Files:**
- Modify: `autofill_agent/extension/content.js`
- Modify: `autofill_agent/extension/background.js`
- Modify: `backend/api/routes/emails.py`

- [ ] **Step 1: Update extension `content.js` to fetch `/api/v1/profile` directly on autofill**
- [ ] **Step 2: Add `POST /api/v1/emails/generate` endpoint for Gemini AI cold email drafting**
- [ ] **Step 3: Add `POST /api/v1/emails/send` endpoint for Gmail OAuth dispatching**

---

### Task 2: Build AI Cold Email Studio & HR Verification Modal Components

**Files:**
- Create: `frontend/src/components/EmailStudio.jsx`
- Create: `frontend/src/components/HrVerificationModal.jsx`
- Modify: `frontend/src/components/JobExplorer.jsx`

- [ ] **Step 1: Build `EmailStudio.jsx` with subject line editor, body text area, regenerate button, and send button**
- [ ] **Step 2: Build `HrVerificationModal.jsx` with HR recruiter name, editable email input, and confirm send button**
- [ ] **Step 3: Add dual action buttons to job cards in `JobExplorer.jsx` and connect email drafting workflow**

---

### Task 3: Integration, Real Job Refresh & Verification

**Files:**
- Modify: `frontend/src/app/page.jsx`
- Modify: `backend/api/routes/jobs.py`

- [ ] **Step 1: Connect `EmailStudio` and `HrVerificationModal` state in `page.jsx`**
- [ ] **Step 2: Connect real job search refresh in `JobExplorer.jsx`**
- [ ] **Step 3: Run `npm run build` and `pytest backend/tests` to verify clean compilation**
