# Unified Backend API Contract
#
# Base URL: http://localhost:8000
# Auth: All endpoints except `/auth/*` and `/health` require:
#   Authorization: Bearer <jwt>
#
# Run from workspace root:
#   pip install -r backend/requirements.txt
#   uvicorn backend.main:app --reload --port 8000

## Auth

### GET `/auth/google`
Returns Google OAuth URL (includes Gmail compose/send scopes).

**Response**
```json
{ "url": "https://accounts.google.com/o/oauth2/v2/auth?..." }
```

### GET `/auth/callback?code=...`
Exchanges OAuth code for JWT and upserts the user (stores Gmail tokens).

**Response**
```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@gmail.com",
    "name": "User",
    "has_gmail_token": true
  }
}
```

### GET `/auth/me`
Current authenticated user.

---

## Resume

### POST `/upload-resume`
Multipart form field: `file` (PDF or DOCX).

Parses with Gemini Flash (deterministic fallback). Returns editable profile.

### GET `/resume/{id}`
Fetch stored profile.

### PUT `/resume/{id}`
Update editable fields before confirm.

**Body**
```json
{
  "contact": { "name": "...", "email": "...", "phone": "...", "linkedin": "..." },
  "skills": ["Python", "React"],
  "experience_years": 2,
  "current_role": "SWE Intern",
  "preferred_roles": ["Backend Engineer"]
}
```

### POST `/resume/{id}/rescan`
Re-parse with Gemini Flash using stored raw text.

### POST `/resume/{id}/confirm`
Marks profile confirmed, runs job search, writes JSON + Excel report under
`backend/reports/{user_id}/{report_id}/`.

**Response** includes `report_id`, `match_count`, and job cards.

---

## Jobs & Reports

### GET `/reports`
List reports for the current user.

### GET `/reports/{id}`
Report JSON with job matches (HR fields may be null until drafts are created).

### GET `/reports/{id}/excel`
Download Excel export.

### GET `/jobs?report_id=`
Job cards for a report.

**Job match fields**
- Company Name (`company_name`)
- Position (`position`)
- Apply Link (`apply_link`)
- Matching Percentage (`matching_percentage`)
- Relevant Skilled Match (`relevant_skills`)
- HR Recruiter Name (`hr_recruiter_name`)
- HR Recruiter Email (`hr_recruiter_email`)

---

## Emails

### POST `/emails/drafts`
Discover recruiters for selected job matches and create Gmail drafts.

**Body**
```json
{ "job_match_ids": [1, 2, 3] }
```

Updates HR fields on matches and refreshes report files.

### GET `/emails/drafts`
List drafts for review.

### POST `/emails/send`
Send approved outreach for draft IDs (creates sent messages via Gmail).

**Body**
```json
{ "draft_ids": [1] }
```

---

## Health

### GET `/health`
```json
{ "status": "ok" }
```

---

## Frontend flow

1. Redirect user to `/auth/google` → Google → `/auth/callback` → store JWT
2. `POST /upload-resume` → show editable fields
3. Optional `PUT /resume/{id}` / `POST /resume/{id}/rescan`
4. `POST /resume/{id}/confirm` → show job cards from response / `GET /jobs`
5. User selects jobs → `POST /emails/drafts`
6. User reviews → `POST /emails/send`
