# Design Specification: Backend & Frontend API Integration

**Date**: 2026-07-31  
**Status**: Approved  

---

## 1. Overview
This specification details the full integration between the newly created Single-Page Web Application (`claude_frontend/landing.html/index.html`) and the unified FastAPI backend (`http://localhost:8000`).

---

## 2. API Endpoints Mapping & Data Flow

```
 Landing Page (/auth/google)
         │
         ▼
 Resume Parser (/upload-resume -> /resume/{id}/confirm)
         │
         ▼
 AI Job Matcher (/jobs -> /emails/drafts -> /emails/send -> /reports/{id}/excel)
```

### 1. Authentication Integration (`/auth/*`)
* **Endpoint**: `GET /auth/google` and `GET /auth/me`
* **UI Action**: Clicking "Continue with Google" or "Get Started" requests the OAuth URL or performs JWT authentication.
* **Header Sync**: Syncs user email, name, and avatar across the header profile badge and candidate fields.

### 2. Resume Parser Integration (`/upload-resume`, `/resume/{id}`, `/resume/{id}/confirm`)
* **Endpoint**: `POST /upload-resume` (multipart form with `file`)
* **UI Action**: Dragging/dropping a PDF or DOCX file posts the resume to the backend. Real parsed profile fields (Contact info, Core Skills, Experience Years, Preferred Roles) are returned and displayed in the editor.
* **Confirmation Trigger**: Clicking **"Save to Matches"** calls `POST /resume/{id}/confirm`, triggering backend job search agents and populating job match cards.

### 3. Job Search, Recruiter Emails & Reports (`/jobs`, `/emails/drafts`, `/emails/send`, `/reports/{id}/excel`)
* **Endpoints**:
  * `GET /jobs?report_id=`: Loads actual matched job cards.
  * `POST /emails/drafts`: Discovers HR recruiters for selected job matches and creates Gmail drafts.
  * `POST /emails/send`: Sends cold email outreach via Gmail API.
  * `GET /reports/{id}/excel`: Downloads structured Excel report.
* **UI Elements Added to Job Match Cards**:
  * Recruiter Name (`hr_recruiter_name`) & Email (`hr_recruiter_email`) badge.
  * **"Generate Cold Email Draft"** button.
  * **"Send Outreach"** button.
  * **"Download Excel Report"** button in Job Matcher header.

### 4. API Client & Fallback Engine (`MewApiClient`)
* A unified JavaScript client handles API requests with `Authorization: Bearer <jwt>` header.
* Checks health endpoint (`GET /health`). If backend is offline, seamlessly falls back to local simulation mode so UI features remain fully functional.

---

## 3. UI Status Badges
* **Backend Status Indicator**: Displayed in the left sidebar:
  * `🟢 Backend Connected` (when FastAPI is active on `http://localhost:8000`)
  * `🟡 Demo Mode` (when backend is offline)

---

## 4. Verification Plan
* Validate authentication request flow.
* Validate resume upload with real PDF/DOCX file against `/upload-resume`.
* Validate profile confirmation calling `/resume/{id}/confirm`.
* Validate Cold Email drafting and sending actions.
* Verify offline fallback mode functions smoothly.
