# Implementation Plan: Job Matcher & Cold Email Studio Integration

We will update [`claude_frontend/landing.html/index.html`](file:///Users/abhi_2467/aura_folder✨/job_applying_agent/claude_frontend/landing.html/index.html) to transform the `#view-matches` view into an interactive job matcher with a fluid Split Cold Email Studio Panel.

## Proposed Changes

### Component: Frontend Single-Page Application (`index.html`)

#### [MODIFY] [`index.html`](file:///Users/abhi_2467/aura_folder✨/job_applying_agent/claude_frontend/landing.html/index.html)

- **Task 1: Add Cold Email Studio Panel and Fluid Split Layout Container in `#view-matches`**
  - Add `#match-deck-container` wrapping job card deck.
  - Add `#cold-email-studio` sidebar panel (hidden by default) with HR recruiter header, subject input, personalized body textarea, **Redraft Email** button, and **Send Outreach via Gmail** button.

- **Task 2: Implement Authentic Application Link Navigation (`applyToCurrentJob`)**
  - Make **"Click to Apply"** open `job.apply_link` in a new browser tab (`window.open(link, '_blank')`).

- **Task 3: Implement Cold Email Recruiter Button & Fluid Panel Toggle (`openColdEmailStudio`)**
  - Clicking **"Cold Email Recruiter"** switches layout from centered card deck to split workspace (cards 45% left, Cold Email Studio 55% right).
  - Populates HR Recruiter Name (`hr_recruiter_name`) & Email (`hr_recruiter_email`).

- **Task 4: Implement Gemini AI Personalized Pitch Generator & Redrafting (`redraftColdEmail`)**
  - `generatePersonalizedPitch(candidate, job, variation)` crafts a 3-paragraph outreach email referencing candidate's name, role, projects, and skills.
  - **"Redraft Email"** button (`#btn-redraft-email`) generates a fresh variation with loading spinner.
  - **"Send Outreach Email"** button (`#btn-send-outreach`) posts to backend and shows success toast.

---

## Verification Plan

### Manual Verification
1. Open `http://localhost:3000/index.html` in browser.
2. Complete login, parse resume, and navigate to `#view-matches`.
3. Click **"Click to Apply"** $\rightarrow$ verifies job application opens in a new tab.
4. Click **"Cold Email Recruiter"** $\rightarrow$ verifies fluid transition into split screen layout with Cold Email Studio Panel.
5. Verify HR recruiter name and email are populated.
6. Click **"Redraft Email"** $\rightarrow$ verifies loading spinner and fresh personalized pitch generation.
7. Click **"Send Outreach via Gmail"** $\rightarrow$ verifies toast confirmation.
