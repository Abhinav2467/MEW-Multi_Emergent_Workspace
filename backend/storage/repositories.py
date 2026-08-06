"""Repository layer for users, profiles, reports, matches, and drafts."""

from __future__ import annotations

import json
from typing import Any

import aiosqlite

from backend.models.schemas import ParsedProfile


class UserRepository:
    def __init__(self, conn: aiosqlite.Connection) -> None:
        self.conn = conn

    async def upsert_google_user(
        self,
        *,
        google_id: str,
        email: str,
        name: str | None,
        gmail_tokens_json: str | None = None,
        google_refresh_token: str | None = None,
    ) -> dict[str, Any]:
        existing = await self.get_by_google_id(google_id)
        if not existing:
            existing = await self.get_by_email(email)

        if existing:
            ref_token = google_refresh_token or existing.get("google_refresh_token")
            if gmail_tokens_json is not None:
                await self.conn.execute(
                    "UPDATE users SET email = ?, name = ?, gmail_tokens_json = ?, google_refresh_token = ?, google_id = ? WHERE id = ?",
                    (email, name, gmail_tokens_json, ref_token, google_id, existing["id"]),
                )
            else:
                await self.conn.execute(
                    "UPDATE users SET email = ?, name = ?, google_refresh_token = ?, google_id = ? WHERE id = ?",
                    (email, name, ref_token, google_id, existing["id"]),
                )
            await self.conn.commit()
            return await self.get_by_id(existing["id"])  # type: ignore[return-value]

        cursor = await self.conn.execute(
            "INSERT INTO users (google_id, email, name, gmail_tokens_json, google_refresh_token) VALUES (?, ?, ?, ?, ?)",
            (google_id, email, name, gmail_tokens_json, google_refresh_token),
        )
        await self.conn.commit()
        return await self.get_by_id(cursor.lastrowid)  # type: ignore[return-value]

    async def get_by_id(self, user_id: int) -> dict[str, Any] | None:
        cursor = await self.conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_by_email(self, email: str) -> dict[str, Any] | None:
        cursor = await self.conn.execute(
            "SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (email.strip(),)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_by_google_id(self, google_id: str) -> dict[str, Any] | None:
        cursor = await self.conn.execute(
            "SELECT * FROM users WHERE google_id = ?", (google_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def update_gmail_tokens(self, user_id: int, tokens_json: str) -> None:
        await self.conn.execute(
            "UPDATE users SET gmail_tokens_json = ? WHERE id = ?",
            (tokens_json, user_id),
        )
        await self.conn.commit()

    async def update_google_refresh_token(self, user_id: int, refresh_token: str) -> None:
        await self.conn.execute(
            "UPDATE users SET google_refresh_token = ? WHERE id = ?",
            (refresh_token, user_id),
        )
        await self.conn.commit()

    async def get_active_or_first_user(self) -> dict[str, Any] | None:
        # 1. Check profile.json for email match first
        try:
            from backend.storage.profile_sync import PROFILE_JSON_PATH
            if PROFILE_JSON_PATH.exists():
                with open(PROFILE_JSON_PATH, "r", encoding="utf-8") as f:
                    pdata = json.load(f)
                    pemail = (pdata.get("personal") or {}).get("email")
                    if pemail:
                        cursor = await self.conn.execute(
                            "SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (pemail.strip(),)
                        )
                        row = await cursor.fetchone()
                        if row:
                            return dict(row)
        except Exception:
            pass

        # 2. Fallback to active user with token or first user
        cursor = await self.conn.execute(
            "SELECT * FROM users WHERE gmail_tokens_json IS NOT NULL OR google_refresh_token IS NOT NULL ORDER BY id DESC LIMIT 1"
        )
        row = await cursor.fetchone()
        if not row:
            cursor = await self.conn.execute("SELECT * FROM users ORDER BY id DESC LIMIT 1")
            row = await cursor.fetchone()
        return dict(row) if row else None


class ProfileRepository:
    def __init__(self, conn: aiosqlite.Connection) -> None:
        self.conn = conn

    async def create(
        self,
        *,
        user_id: int,
        profile: ParsedProfile,
        parse_method: str,
        resume_file_path: str | None,
    ) -> dict[str, Any]:
        cursor = await self.conn.execute(
            """
            INSERT INTO profiles (user_id, parsed_json, parse_method, resume_file_path, version)
            VALUES (?, ?, ?, ?, 1)
            """,
            (
                user_id,
                profile.model_dump_json(),
                parse_method,
                resume_file_path,
            ),
        )
        await self.conn.commit()
        return await self.get(cursor.lastrowid)  # type: ignore[arg-type]

    async def get(self, profile_id: int) -> dict[str, Any] | None:
        cursor = await self.conn.execute(
            "SELECT * FROM profiles WHERE id = ?", (profile_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_for_user(self, profile_id: int, user_id: int) -> dict[str, Any] | None:
        cursor = await self.conn.execute(
            "SELECT * FROM profiles WHERE id = ? AND user_id = ?",
            (profile_id, user_id),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_latest_for_user(self, user_id: int) -> dict[str, Any] | None:
        cursor = await self.conn.execute(
            "SELECT * FROM profiles WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_latest(self) -> dict[str, Any] | None:
        cursor = await self.conn.execute(
            "SELECT * FROM profiles ORDER BY id DESC LIMIT 1"
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def update_parsed(
        self,
        profile_id: int,
        profile: ParsedProfile,
        parse_method: str | None = None,
    ) -> dict[str, Any]:
        if parse_method:
            await self.conn.execute(
                """
                UPDATE profiles
                SET parsed_json = ?, parse_method = ?, version = version + 1,
                    updated_at = datetime('now')
                WHERE id = ?
                """,
                (profile.model_dump_json(), parse_method, profile_id),
            )
        else:
            await self.conn.execute(
                """
                UPDATE profiles
                SET parsed_json = ?, version = version + 1, updated_at = datetime('now')
                WHERE id = ?
                """,
                (profile.model_dump_json(), profile_id),
            )
        await self.conn.commit()
        return await self.get(profile_id)  # type: ignore[return-value]

    async def confirm(self, profile_id: int) -> dict[str, Any]:
        await self.conn.execute(
            """
            UPDATE profiles
            SET confirmed_at = datetime('now'), updated_at = datetime('now')
            WHERE id = ?
            """,
            (profile_id,),
        )
        await self.conn.commit()
        return await self.get(profile_id)  # type: ignore[return-value]

    @staticmethod
    def parse_profile(record: dict[str, Any]) -> ParsedProfile:
        return ParsedProfile.model_validate_json(record["parsed_json"])


class ReportRepository:
    def __init__(self, conn: aiosqlite.Connection) -> None:
        self.conn = conn

    async def create(
        self,
        *,
        user_id: int,
        profile_id: int,
        status: str = "pending",
    ) -> dict[str, Any]:
        cursor = await self.conn.execute(
            """
            INSERT INTO job_reports (user_id, profile_id, status)
            VALUES (?, ?, ?)
            """,
            (user_id, profile_id, status),
        )
        await self.conn.commit()
        return await self.get(cursor.lastrowid)  # type: ignore[arg-type]

    async def get(self, report_id: int) -> dict[str, Any] | None:
        cursor = await self.conn.execute(
            "SELECT * FROM job_reports WHERE id = ?", (report_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_for_user(self, report_id: int, user_id: int) -> dict[str, Any] | None:
        cursor = await self.conn.execute(
            "SELECT * FROM job_reports WHERE id = ? AND user_id = ?",
            (report_id, user_id),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def list_for_user(self, user_id: int) -> list[dict[str, Any]]:
        cursor = await self.conn.execute(
            "SELECT * FROM job_reports WHERE user_id = ? ORDER BY id DESC",
            (user_id,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def complete(
        self,
        report_id: int,
        *,
        json_path: str,
        excel_path: str,
        status: str = "ready",
    ) -> dict[str, Any]:
        await self.conn.execute(
            """
            UPDATE job_reports
            SET json_path = ?, excel_path = ?, status = ?
            WHERE id = ?
            """,
            (json_path, excel_path, status, report_id),
        )
        await self.conn.commit()
        return await self.get(report_id)  # type: ignore[return-value]

    async def set_status(self, report_id: int, status: str) -> None:
        await self.conn.execute(
            "UPDATE job_reports SET status = ? WHERE id = ?",
            (status, report_id),
        )
        await self.conn.commit()


class JobMatchRepository:
    def __init__(self, conn: aiosqlite.Connection) -> None:
        self.conn = conn

    async def bulk_create(self, report_id: int, matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
        created: list[dict[str, Any]] = []
        for m in matches:
            cursor = await self.conn.execute(
                """
                INSERT INTO job_matches (
                    report_id, company_name, position, apply_link,
                    matching_percentage, relevant_skills,
                    hr_recruiter_name, hr_recruiter_email, location, job_type, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report_id,
                    m["company_name"],
                    m["position"],
                    m["apply_link"],
                    m["matching_percentage"],
                    m.get("relevant_skills", ""),
                    m.get("hr_recruiter_name"),
                    m.get("hr_recruiter_email"),
                    m.get("location"),
                    m.get("job_type"),
                    m.get("created_at"),
                ),
            )
            row = await self.get(cursor.lastrowid)  # type: ignore[arg-type]
            if row:
                created.append(row)
        await self.conn.commit()
        return created

    async def get(self, match_id: int) -> dict[str, Any] | None:
        cursor = await self.conn.execute(
            "SELECT * FROM job_matches WHERE id = ?", (match_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def list_for_report(self, report_id: int) -> list[dict[str, Any]]:
        cursor = await self.conn.execute(
            "SELECT * FROM job_matches WHERE report_id = ? ORDER BY created_at DESC, matching_percentage DESC",
            (report_id,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def update_hr(
        self,
        match_id: int,
        *,
        hr_recruiter_name: str | None,
        hr_recruiter_email: str | None,
    ) -> None:
        await self.conn.execute(
            """
            UPDATE job_matches
            SET hr_recruiter_name = ?, hr_recruiter_email = ?
            WHERE id = ?
            """,
            (hr_recruiter_name, hr_recruiter_email, match_id),
        )
        await self.conn.commit()


class DraftRepository:
    def __init__(self, conn: aiosqlite.Connection) -> None:
        self.conn = conn

    async def create(
        self,
        *,
        user_id: int,
        job_match_id: int,
        gmail_draft_id: str | None = None,
        status: str = "draft",
        error: str | None = None,
    ) -> dict[str, Any]:
        cursor = await self.conn.execute(
            """
            INSERT INTO email_drafts (user_id, job_match_id, gmail_draft_id, status, error)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, job_match_id, gmail_draft_id, status, error),
        )
        await self.conn.commit()
        return await self.get(cursor.lastrowid)  # type: ignore[arg-type]

    async def get(self, draft_id: int) -> dict[str, Any] | None:
        cursor = await self.conn.execute(
            "SELECT * FROM email_drafts WHERE id = ?", (draft_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_for_user(self, draft_id: int, user_id: int) -> dict[str, Any] | None:
        cursor = await self.conn.execute(
            "SELECT * FROM email_drafts WHERE id = ? AND user_id = ?",
            (draft_id, user_id),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def list_for_user(self, user_id: int) -> list[dict[str, Any]]:
        cursor = await self.conn.execute(
            "SELECT * FROM email_drafts WHERE user_id = ? ORDER BY id DESC",
            (user_id,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def mark_sent(self, draft_id: int) -> None:
        await self.conn.execute(
            """
            UPDATE email_drafts
            SET status = 'sent', sent_at = datetime('now')
            WHERE id = ?
            """,
            (draft_id,),
        )
        await self.conn.commit()


class AppliedJobRepository:
    def __init__(self, conn: aiosqlite.Connection) -> None:
        self.conn = conn

    async def record_application(
        self,
        *,
        user_id: int,
        company_name: str,
        position: str,
        apply_link: str,
        location: str | None = None,
        matching_percentage: int = 0,
        relevant_skills: str | None = None,
        hr_recruiter_name: str | None = None,
        hr_recruiter_email: str | None = None,
        cold_email_sent: bool = False,
    ) -> dict[str, Any]:
        cursor = await self.conn.execute(
            """
            SELECT id FROM applied_jobs WHERE user_id = ? AND company_name = ? AND position = ?
            """,
            (user_id, company_name, position),
        )
        existing = await cursor.fetchone()
        if existing:
            await self.conn.execute(
                """
                UPDATE applied_jobs
                SET apply_link = ?, location = ?, matching_percentage = ?, relevant_skills = ?,
                    hr_recruiter_name = ?, hr_recruiter_email = ?,
                    cold_email_sent = CASE WHEN ? = 1 THEN 1 ELSE cold_email_sent END
                WHERE id = ?
                """,
                (
                    apply_link,
                    location,
                    matching_percentage,
                    relevant_skills,
                    hr_recruiter_name,
                    hr_recruiter_email,
                    1 if cold_email_sent else 0,
                    existing[0],
                ),
            )
            await self.conn.commit()
            res = await self.get_by_id(existing[0])
            return res if res else {}

        cursor = await self.conn.execute(
            """
            INSERT INTO applied_jobs (
                user_id, company_name, position, apply_link, location,
                matching_percentage, relevant_skills, hr_recruiter_name,
                hr_recruiter_email, cold_email_sent
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                company_name,
                position,
                apply_link,
                location,
                matching_percentage,
                relevant_skills,
                hr_recruiter_name,
                hr_recruiter_email,
                1 if cold_email_sent else 0,
            ),
        )
        await self.conn.commit()
        res = await self.get_by_id(cursor.lastrowid)
        return res if res else {}

    async def get_by_id(self, app_id: int) -> dict[str, Any] | None:
        cursor = await self.conn.execute(
            "SELECT * FROM applied_jobs WHERE id = ?", (app_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def list_for_user(self, user_id: int) -> list[dict[str, Any]]:
        cursor = await self.conn.execute(
            "SELECT * FROM applied_jobs WHERE user_id = ? ORDER BY id DESC",
            (user_id,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def update_cold_email_status(
        self,
        *,
        user_id: int,
        company_name: str,
        position: str | None = None,
        cold_email_sent: bool = True,
    ) -> None:
        if position:
            await self.conn.execute(
                """
                UPDATE applied_jobs
                SET cold_email_sent = ?
                WHERE user_id = ? AND LOWER(company_name) = LOWER(?) AND LOWER(position) = LOWER(?)
                """,
                (1 if cold_email_sent else 0, user_id, company_name, position),
            )
        else:
            await self.conn.execute(
                """
                UPDATE applied_jobs
                SET cold_email_sent = ?
                WHERE user_id = ? AND LOWER(company_name) = LOWER(?)
                """,
                (1 if cold_email_sent else 0, user_id, company_name),
            )
        await self.conn.commit()


class ResumeHistoryRepository:
    def __init__(self, conn: aiosqlite.Connection) -> None:
        self.conn = conn

    async def record_resume(
        self,
        *,
        user_id: int,
        filename: str,
        file_size_bytes: int = 0,
        status: str = "Completed",
    ) -> dict[str, Any]:
        cursor = await self.conn.execute(
            """
            INSERT INTO resume_history (user_id, filename, file_size_bytes, status)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, filename, file_size_bytes, status),
        )
        await self.conn.commit()
        row_id = cursor.lastrowid
        cursor_res = await self.conn.execute(
            "SELECT * FROM resume_history WHERE id = ?", (row_id,)
        )
        row = await cursor_res.fetchone()
        return dict(row) if row else {}

    async def list_for_user(self, user_id: int) -> list[dict[str, Any]]:
        cursor = await self.conn.execute(
            "SELECT * FROM resume_history WHERE user_id = ? ORDER BY id DESC",
            (user_id,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

