# Technical Design Spec: Email Security Authorization & User-Scoped Resume History

**Date:** 2026-08-15  
**Topic:** Fixing Email Impersonation / Duplicate Email Vulnerabilities and Resume Parsing History Multi-Tenant Isolation

---

## 1. Overview & Problem Statement

### Issue 1: Email Impersonation & Security Flaw
Currently, when a user edits their profile email field (e.g., via `PUT /api/v1/profile`), the system updates `profile.json` without validating if the new email belongs to another registered user in the database (`users` table). 
Subsequently, during cold email drafting (`POST /api/v1/emails/save-draft`) or sending (`POST /api/v1/emails/send`), backend helper routines (such as `UserRepository.get_active_or_first_user()`) lookup users by matching `profile.json`'s email against the `users` table. 

This creates a critical security vulnerability:
- If **User 1** edits their profile email to **User 2's** registered email, backend queries match User 2 in the database and load User 2's stored `gmail_tokens_json`.
- User 1 can then send/draft emails dispatched directly from User 2's Gmail address using User 2's OAuth tokens.

### Issue 2: Resume History Shared Across Users
In the Resume Parser UI, the history of parsed resumes is currently leaking across accounts. All users see a common list of past parsed resumes.
Investigation revealed two root causes:
1. `ResumeHistoryRepository.list_for_user(user_id)` contains SQL: `WHERE user_id = ? OR user_id = 1`, which explicitly appends User 1's history to all users.
2. Unauthenticated calls and browser `localStorage` fallbacks use a single global key (`mew_resume_history`) shared across all sessions on the device.

---

## 2. Proposed Architecture & Security Controls

### Component 1: Email Security & Verification Enforcer

#### 1.1 Duplicate Email Check (`PUT /api/v1/profile`, `PUT /resume/{profile_id}`)
When a logged-in user edits their profile email:
- Retrieve the authenticated user (`current_user`) via JWT token (`get_current_user`).
- If `new_email != current_user["email"]`:
  - Query `UserRepository.get_by_email(new_email)`.
  - If a user row exists where `existing_user["id"] != current_user["id"]`:
    - **Reject update with HTTP 400**:
      `"You can't use this email. It's registered with another user, and you can't use it."`
    - Do NOT persist the email change to `profile.json` or database.

#### 1.2 Google OAuth Re-Verification for Unverified Emails
- If `new_email` is NOT registered to another user, but differs from `current_user["email"]`:
  - Update profile email, but set `requires_google_reauth = True` in response.
  - Require the user to re-authenticate with Google Auth under their user ID to store Google OAuth tokens for that email under their `user.id` in `users` table.
- When Google OAuth callback executes (`GET /auth/callback`):
  - Tokens are saved strictly for `current_user.id` in `users` table.

#### 1.3 Strict OAuth Token Scoping (No Impersonation)
- In `backend/api/routes/emails.py` (`save-draft` & `send`):
  - Require authenticated user JWT token (`get_current_user`).
  - Retrieve `gmail_tokens_json` strictly by `user["id"]` from `users` table.
  - Remove `profile.json` email lookup from `UserRepository.get_active_or_first_user()` to prevent token cross-contamination.
  - If `user["gmail_tokens_json"]` is missing or user's email is unverified for Gmail OAuth under their `user_id`:
    - Return HTTP 400 prompting Google OAuth re-verification under their account.

---

### Component 2: User-Scoped Resume Parsing History

#### 2.1 Database Query Scoping
- In `backend/storage/repositories.py`:
  - Modify `ResumeHistoryRepository.list_for_user(user_id)` SQL:
    ```sql
    -- Old: SELECT * FROM resume_history WHERE user_id = ? OR user_id = 1 ORDER BY id DESC
    -- New:
    SELECT * FROM resume_history WHERE user_id = ? ORDER BY id DESC
    ```
  - Modify `AppliedJobRepository.list_for_user(user_id)` SQL:
    ```sql
    -- Old: SELECT * FROM applied_jobs WHERE user_id = ? OR user_id = 1 ORDER BY id DESC
    -- New:
    SELECT * FROM applied_jobs WHERE user_id = ? ORDER BY id DESC
    ```

#### 2.2 Endpoint Authorization
- In `backend/api/routes/resume.py`:
  - `GET /api/v1/resume/history`:
    - Validate JWT token.
    - If unauthenticated / guest, return empty array `[]`.
    - If authenticated, return history strictly for `user["id"]`.

#### 2.3 Frontend Storage & UI Scoping
- In `claude_frontend/landing.html/index.html` & `frontend/src/components/ResumeStudio.jsx`:
  - Include Bearer token in requests to `/api/v1/resume/history`.
  - Scope local storage fallback key by user email: `mew_resume_history_${user.email}`.
  - Clear history element on user logout.

---

## 3. Verification & Testing Plan

### Automated Tests
- Unit test for duplicate email edit rejection: Attempt updating email to an existing registered user's email -> verify HTTP 400 error message `"You can't use this email. It's registered with another user, and you can't use it."`
- Unit test for token isolation: Attempt saving draft as User 1 with User 2's email -> verify draft fails or uses User 1's tokens only.
- Unit test for resume history scoping: Create resumes for User 1 and User 2 -> verify `GET /api/v1/resume/history` for User 2 returns ONLY User 2's resumes.

### Manual Verification
- Log in as User 1, edit email to User 2's email -> verify exact error banner appears.
- Log in as User 2, upload resume -> verify User 1 cannot see User 2's resume in history.

