# Design Specification: Landing Sidebar Hiding, Real Resume Parsing & Extension Profile Sync

**Date**: 2026-07-31  
**Status**: Approved  

---

## 1. Overview
This specification details:
1. Removing the left sidebar completely on the Landing Page (`#view-landing`).
2. Linking the Resume Parser Workspace (`#view-parser`) with the FastAPI backend endpoint `/api/v1/parse-resume` (and `/upload-resume`) to parse PDF/DOCX resumes via Gemini Flash AI.
3. Adding profile sync endpoint `/api/v1/sync-profile` to write candidate edits to `autofill_agent/backend/data/profile.json` so the Chrome Extension performs 0.4s autofill on job boards.

---

## 2. Detailed Architecture & Design

### A. Landing Page Layout (No Sidebar)
* **Sidebar Visibility**:
  * On `#view-landing`: The `<aside>` element is hidden (`display: none`), and main container padding is reset to `pl-0` (full width `left-0`).
  * On `#view-parser`, `#view-matches`, `#view-dashboard`: The `<aside>` element is displayed (`block`), and padding resets to `pl-72` (left `left-72`).
* Dynamic sidebar toggle implemented inside `MewRouter.navigateTo(viewName)`.

---

### B. Real Resume Parsing Backend Integration
* **File Upload Trigger**:
  * Dragging & dropping or selecting a PDF/DOCX resume posts the raw file to `POST http://localhost:8000/api/v1/parse-resume` via `FormData`.
* **Data Binding**:
  * Response parsed by Gemini Flash AI populates:
    * Candidate Name $\rightarrow$ `#preview-name` & header badge.
    * Email $\rightarrow$ `#parsed-email`.
    * Phone $\rightarrow$ `#parsed-phone`.
    * Location $\rightarrow$ `#parsed-location`.
    * Current Title $\rightarrow$ `#parsed-title`.
    * Core Skills $\rightarrow$ Renders tags in `#skills-container`.
    * Resume Filename $\rightarrow$ `#preview-filename` & live parsing queue list.

---

### C. Chrome Extension Profile Sync (`profile.json`)
* **New Sync Endpoint**:
  * `POST http://localhost:8000/api/v1/sync-profile` in `backend/api/routes/autofill.py`.
  * Accepts candidate form edits (`name`, `email`, `phone`, `location`, `current_title`, `skills`, `github_url`).
  * Writes to `autofill_agent/backend/data/profile.json` via `sync_profile_to_autofill_json()`.
* **"Save to Matches" Action**:
  * Gathers current DOM values from contact fields and skills tags.
  * Calls `/api/v1/sync-profile`.
  * Displays success notification: **"Profile saved & synced with Chrome Extension"**.
  * Advances progress stepper and navigates to `#view-matches`.

---

## 3. Verification Plan
* Test `#view-landing` renders full width without sidebar.
* Test uploading a PDF resume calls `/api/v1/parse-resume` and fills all fields.
* Test clicking "Save to Matches" updates `profile.json` for extension autofill.
