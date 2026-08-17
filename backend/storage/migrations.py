"""Database schema migrations."""

from __future__ import annotations

import aiosqlite

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    google_id TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    name TEXT,
    gmail_tokens_json TEXT,
    google_refresh_token TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    parsed_json TEXT NOT NULL,
    parse_method TEXT NOT NULL DEFAULT 'deterministic',
    confirmed_at TEXT,
    resume_file_path TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS job_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    profile_id INTEGER NOT NULL,
    json_path TEXT,
    excel_path TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
);

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

CREATE TABLE IF NOT EXISTS email_drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    job_match_id INTEGER NOT NULL,
    gmail_draft_id TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    error TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    sent_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (job_match_id) REFERENCES job_matches(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS applied_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    company_name TEXT NOT NULL,
    position TEXT NOT NULL,
    apply_link TEXT NOT NULL,
    location TEXT,
    matching_percentage INTEGER NOT NULL DEFAULT 0,
    relevant_skills TEXT,
    hr_recruiter_name TEXT,
    hr_recruiter_email TEXT,
    cold_email_sent INTEGER NOT NULL DEFAULT 0,
    applied_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS resume_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    filename TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'Completed',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_profiles_user ON profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_reports_user ON job_reports(user_id);
CREATE INDEX IF NOT EXISTS idx_matches_report ON job_matches(report_id);
CREATE INDEX IF NOT EXISTS idx_drafts_user ON email_drafts(user_id);
CREATE INDEX IF NOT EXISTS idx_applied_user ON applied_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_resume_user ON resume_history(user_id);
"""


async def run_migrations(conn: aiosqlite.Connection) -> None:
    await conn.executescript(SCHEMA_SQL)
    try:
        await conn.execute("ALTER TABLE job_matches ADD COLUMN created_at TEXT")
    except Exception:
        pass
    try:
        await conn.execute("ALTER TABLE users ADD COLUMN google_refresh_token TEXT")
    except Exception:
        pass
    # Ensure default guest user (id=1) exists so foreign keys never fail for unauthenticated API requests
    try:
        await conn.execute(
            """
            INSERT INTO users (id, google_id, email, name)
            VALUES (1, 'guest_user_1', 'candidate@mew.ai', 'Guest Candidate')
            ON CONFLICT(id) DO NOTHING
            """
        )
        # Purge legacy guest test records so unauthenticated guest sessions start with clean history
        await conn.execute("DELETE FROM resume_history WHERE user_id = 1")
    except Exception as exc:
        print(f"[Warning] Seed guest user migration notice: {exc}")
    await conn.commit()


