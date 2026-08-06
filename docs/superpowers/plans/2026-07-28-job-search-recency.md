# Job Search 22-Day Recency and Timestamp Sorting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Modify job searching agent to store and sort job listing timestamps (`created_at`) across database, API routes, and reports.

**Architecture:** Extend SQLite database schema with `created_at TEXT` on `job_matches`, persist timestamp during job matching pipeline, and sort repository outputs by `created_at DESC`.

**Tech Stack:** Python 3.13, SQLite (`aiosqlite`), FastAPI, Pydantic, Pytest.

## Global Constraints

- Recency window: 22 days (`job_recency_days = 22`)
- Sorting rule: `ORDER BY created_at DESC, matching_percentage DESC`

---

### Task 1: Database Migration & JobMatchRepository Update

**Files:**
- Modify: `backend/storage/migrations.py:30-55`
- Modify: `backend/storage/repositories.py:225-275`
- Test: `backend/tests/test_job_recency.py`

**Interfaces:**
- Consumes: Job dictionary containing `"created_at"` string.
- Produces: `job_matches` database records containing `created_at` timestamp column.

- [ ] **Step 1: Write the failing test**

Edit `backend/tests/test_job_recency.py` to add `test_job_match_repository_persists_and_sorts_created_at`:

```python
import pytest
import aiosqlite
from backend.storage.migrations import run_migrations
from backend.storage.repositories import JobMatchRepository, ReportRepository, ProfileRepository
from backend.models.schemas import ParsedProfile, ContactInfo

@pytest.mark.asyncio
async def test_job_match_repository_persists_and_sorts_created_at():
    async with aiosqlite.connect(":memory:") as conn:
        conn.row_factory = aiosqlite.Row
        await run_migrations(conn)
        
        prof_repo = ProfileRepository(conn)
        profile = await prof_repo.create(user_id=1, profile=ParsedProfile(contact=ContactInfo(name="Test")), parse_method="test", resume_file_path=None)
        rep_repo = ReportRepository(conn)
        report = await rep_repo.create(user_id=1, profile_id=profile["id"])
        
        match_repo = JobMatchRepository(conn)
        matches = [
            {
                "company_name": "OlderCo",
                "position": "Dev",
                "apply_link": "https://older.com",
                "matching_percentage": 90,
                "relevant_skills": "Python",
                "created_at": "2026-07-10T10:00:00Z",
            },
            {
                "company_name": "NewerCo",
                "position": "Dev",
                "apply_link": "https://newer.com",
                "matching_percentage": 70,
                "relevant_skills": "Python",
                "created_at": "2026-07-25T10:00:00Z",
            },
        ]
        await match_repo.bulk_create(report["id"], matches)
        listed = await match_repo.list_for_report(report["id"])
        assert len(listed) == 2
        assert listed[0]["company_name"] == "NewerCo"
        assert listed[0]["created_at"] == "2026-07-25T10:00:00Z"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `backend/.venv/bin/pytest backend/tests/test_job_recency.py -k test_job_match_repository_persists_and_sorts_created_at`
Expected: FAIL with missing column or assertion error.

- [ ] **Step 3: Update `SCHEMA_SQL` and `JobMatchRepository`**

In `backend/storage/migrations.py`:
```sql
CREATE TABLE IF NOT EXISTS job_matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL,
    company_name TEXT NOT NULL,
    position TEXT NOT NULL,
    apply_link TEXT NOT NULL,
    matching_percentage INTEGER NOT NULL DEFAULT 0,
    relevant_skills TEXT NOT NULL DEFAULT '',
    hr_recruiter_name TEXT,
    hr_recruiter_email TEXT,
    location TEXT,
    job_type TEXT,
    created_at TEXT,
    FOREIGN KEY (report_id) REFERENCES job_reports(id) ON DELETE CASCADE
);
```
And add automatic column migration in `run_migrations`:
```python
    try:
        await conn.execute("ALTER TABLE job_matches ADD COLUMN created_at TEXT")
        await conn.commit()
    except Exception:
        pass
```

In `backend/storage/repositories.py`:
Update `bulk_create` SQL insert to include `created_at`, and update `list_for_report`:
```python
    async def list_for_report(self, report_id: int) -> list[dict[str, Any]]:
        cursor = await self.conn.execute(
            "SELECT * FROM job_matches WHERE report_id = ? ORDER BY created_at DESC, matching_percentage DESC",
            (report_id,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `backend/.venv/bin/pytest backend/tests/test_job_recency.py`
Expected: PASS

- [ ] **Step 5: Commit changes**

Run:
```bash
git add backend/storage/migrations.py backend/storage/repositories.py backend/tests/test_job_recency.py
git commit -m "feat: add created_at to job_matches and sort list_for_report by timestamp"
```

---

### Task 2: Pydantic Schema and API Route Updates

**Files:**
- Modify: `backend/models/schemas.py`
- Modify: `backend/api/routes/jobs.py`
- Test: `backend/tests/test_core.py`

**Interfaces:**
- Consumes: Database `job_matches` dict containing `created_at`.
- Produces: `JobMatchOut` model containing `created_at: str | None`.

- [ ] **Step 1: Write the failing test**

Add test to `backend/tests/test_core.py`:
```python
def test_job_match_out_schema_includes_created_at():
    from backend.models.schemas import JobMatchOut
    out = JobMatchOut(
        id=1,
        report_id=1,
        company_name="TestCo",
        position="Dev",
        apply_link="https://test.com",
        matching_percentage=80,
        relevant_skills="Python",
        created_at="2026-07-20T10:00:00Z",
    )
    assert out.created_at == "2026-07-20T10:00:00Z"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `backend/.venv/bin/pytest backend/tests/test_core.py -k test_job_match_out_schema_includes_created_at`
Expected: FAIL due to unknown attribute or validation error.

- [ ] **Step 3: Update `JobMatchOut` and `_match_out`**

In `backend/models/schemas.py`:
```python
class JobMatchOut(BaseModel):
    id: int
    report_id: int
    company_name: str
    position: str
    apply_link: str
    matching_percentage: int
    relevant_skills: str
    hr_recruiter_name: str | None = None
    hr_recruiter_email: str | None = None
    location: str | None = None
    job_type: str | None = None
    created_at: str | None = None
```

In `backend/api/routes/jobs.py`:
```python
def _match_out(m: dict[str, Any]) -> JobMatchOut:
    return JobMatchOut(
        id=m["id"],
        report_id=m["report_id"],
        company_name=m["company_name"],
        position=m["position"],
        apply_link=m["apply_link"],
        matching_percentage=m["matching_percentage"],
        relevant_skills=m.get("relevant_skills") or "",
        hr_recruiter_name=m.get("hr_recruiter_name"),
        hr_recruiter_email=m.get("hr_recruiter_email"),
        location=m.get("location"),
        job_type=m.get("job_type"),
        created_at=m.get("created_at"),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `backend/.venv/bin/pytest backend/tests/test_core.py`
Expected: PASS

- [ ] **Step 5: Commit changes**

Run:
```bash
git add backend/models/schemas.py backend/api/routes/jobs.py backend/tests/test_core.py
git commit -m "feat: add created_at field to JobMatchOut schema and jobs route response"
```
