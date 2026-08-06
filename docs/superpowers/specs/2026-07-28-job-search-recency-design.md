# Job Searching Agent: 22-Day Recency & Timestamp Sorting Design

## Goal
Modify the job searching agent to fetch jobs posted within the past 22 days and consistently sort them by their listing timestamp (`created_at`) across the API, database repositories, and report outputs.

## Proposed Changes

### 1. Database Schema (`backend/storage/migrations.py`)
- Add `created_at TEXT` column to the `job_matches` table schema definition.
- Execute an `ALTER TABLE job_matches ADD COLUMN created_at TEXT;` migration (wrapped in a try/except or column presence check) so existing databases gain the `created_at` column.

### 2. Storage Repositories (`backend/storage/repositories.py`)
- Update `JobMatchRepository.bulk_create()` to store the `created_at` timestamp from job objects into SQLite.
- Update `JobMatchRepository.list_for_report()` query from:
  `ORDER BY matching_percentage DESC`
  to:
  `ORDER BY created_at DESC, matching_percentage DESC`

### 3. Pydantic Schemas & Routes (`backend/models/schemas.py`, `backend/api/routes/jobs.py`)
- Add `created_at: str | None = None` field to `JobMatchOut` in `backend/models/schemas.py`.
- Map `created_at=m.get("created_at")` in `_match_out()` helper function in `backend/api/routes/jobs.py`.

### 4. Search & Recency Logic (`backend/agents/job_search/careerzenith.py` & `matcher.py`)
- Ensure `fetch_recent_jobs(days=22)` filters jobs with `created_at >= cutoff` (22 days window).
- Ensure `score_jobs` sorts candidates by `created_at` descending (newest first).

## Verification Plan
1. Run `pytest backend/tests/test_job_recency.py` to verify recency filtering and timestamp sorting.
2. Run full backend test suite (`pytest backend/tests`).
