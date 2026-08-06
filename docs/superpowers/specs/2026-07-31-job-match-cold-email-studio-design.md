# Design Specification: Job Matcher & Cold Email Studio Integration

## Goal
Integrate the job finding agent and cold email agent into the single-page application (`claude_frontend/landing.html/index.html`). Enable authentic external job portal navigation, fluid split-screen studio transitions, HR recruiter lead fetching, personalized project-aware email drafting via Gemini AI, and live email redrafting.

## Architecture

### 1. Job Card Stack & External Application Navigation
- **Click to Apply**:
  - Bound to `job.apply_link` (Greenhouse, Lever, Workday).
  - Calling `applyToCurrentJob()` triggers `window.open(job.apply_link, '_blank')`.

### 2. Split Workspace & Cold Email Studio Panel
- Layout in `#view-matches`:
  - Contains `#match-deck-container` (centered card stack or left 40% panel) and `#cold-email-studio` (right 60% panel, initially hidden).
  - Toggling studio state:
    - `#btn-open-email-studio`: Sets `#match-deck-container` class to `w-full lg:w-5/12`, reveals `#cold-email-studio` (`w-full lg:w-7/12 flex flex-col`).
    - `#btn-close-email-studio`: Hides `#cold-email-studio` and resets `#match-deck-container` to `w-full max-w-xl mx-auto`.

### 3. HR Lead Fetching & Personalized Email Draft (Gemini AI)
- **Recruiter Lead Info**:
  - Displays `hr_recruiter_name` (or extracted default) and `hr_recruiter_email` (or `recruiter@company.com`).
- **Personalized Email Pitch Generator**:
  - `generatePersonalizedPitch(candidate, job, variation)`:
    - Extracts candidate's parsed name, current title, key skills, and experience items.
    - Generates a 3-paragraph pitch highlighting real projects, role fit, and value proposition for the job.

### 4. Redraft & Send Outreach Controls
- **Redraft Email (`#btn-redraft-email`)**:
  - Re-triggers pitch generator with a new style/variation angle, showing a spinner on the button.
- **Send Outreach (`#btn-send-outreach`)**:
  - Posts draft payload to `POST http://localhost:8000/api/v1/drafts` or sends via Gmail endpoint.
  - Displays toast notification: `"Outreach Email Sent via Gmail!"`.
