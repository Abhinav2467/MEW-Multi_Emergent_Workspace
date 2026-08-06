# Project MEW — AI Cold Email Drafting Engine & Gmail OAuth Send Design Spec

**Date:** 2026-07-29  
**Status:** Approved  
**Aesthetic Style:** Gen-Z Cyber-Brutalist (Obsidian `#08090a`, Electric Lime `#ccff00`, Cyber Violet `#8a2be2`)  

---

## 1. Executive Summary

Project MEW will expand its consumer platform with a complete **AI Cold Email Drafting Engine**, **HR Recruiter Verification Modal**, **Direct Gmail OAuth Dispatching**, and **Chrome Extension Live Profile Synchronization**.

Every matched job opportunity card in `JobExplorer.jsx` will feature two distinct action buttons (`[⚡ Autofill Application]` and `[✉️ Draft AI Cold Email]`). Clicking `[✉️ Draft AI Cold Email]` generates a personalized cold email using Gemini AI, allows instant editing and regeneration, and dispatches the email via Gmail API using persistent Google OAuth refresh tokens after HR recruiter verification.

---

## 2. Component Architecture & Workflow

### 2.1 Extension Plugin Profile Sync Fix
- Update `autofill_agent/extension/content.js` and `background.js` so `FETCH_MEW_PAYLOAD` fetches live profile data directly from `/api/v1/profile` & `/autofill/preview` instead of relying on stale `chrome.storage.local`.
- Update `PUT /api/v1/profile` to save directly to `autofill_agent/backend/data/profile.json` and broadcast immediate memory sync events.

### 2.2 AI Cold Email Drafting Studio (`JobExplorer.jsx` & `EmailStudio.jsx`)
- **Dual Buttons per Job Card**:
  1. `[⚡ Autofill Application]` (opens ATS application page).
  2. `[✉️ Draft AI Cold Email]` (triggers Gemini AI cold email generation).
- **Drafting Animation**: Displays pulsing loading bar: `[🤖 Gemini AI drafting personalized email...]`.
- **Cold Email Editor Component**:
  - Editable Subject Line input field.
  - Editable Email Body textarea.
  - Recruiter Name & Recruiter Email fields.
  - `[🔄 Regenerate Email]` button (calls Gemini AI with alternate prompt settings).
  - `[🚀 Send Email via Gmail OAuth]` button (triggers verification modal).

### 2.3 HR Recruiter Verification Modal (`HrVerificationModal.jsx`)
- Displays preview of target recruiter info:
  - Recruiter Name (e.g. `Talent Acquisition Lead`).
  - Recruiter Email (Editable input field, default `hr@company.com`).
  - Email Subject & Body summary.
  - `[CONFIRM & SEND NOW VIA GMAIL OAUTH]` button.
- Sends POST to `/api/v1/emails/send`, which retrieves stored `google_refresh_token` from SQLite database and uses Gmail API to send the email directly from candidate's Gmail account!

### 2.4 Real Live Job Recency Search
- Update `GET /api/v1/jobs/recency-feed` and `POST /api/v1/jobs/search` to fetch dynamic, real job matches from SQLite DB / external feed matching candidate skills.
