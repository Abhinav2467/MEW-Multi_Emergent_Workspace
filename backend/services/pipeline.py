"""Confirm-profile pipeline: job search + report (no cold email)."""

from __future__ import annotations

import logging
from typing import Any

import aiosqlite

from backend.agents.job_search.careerzenith import fetch_recent_jobs
from backend.agents.job_search.link_checker import filter_alive_apply_links
from backend.agents.job_search.matcher import score_jobs
from backend.config import get_settings
from backend.models.schemas import ParsedProfile
from backend.services.report import write_report_files
from backend.storage.repositories import (
    JobMatchRepository,
    ProfileRepository,
    ReportRepository,
)

logger = logging.getLogger(__name__)


async def run_job_search_pipeline(
    conn: aiosqlite.Connection,
    *,
    user_id: int,
    profile_id: int,
    profile: ParsedProfile,
) -> dict[str, Any]:
    settings = get_settings()
    profile_repo = ProfileRepository(conn)
    report_repo = ReportRepository(conn)
    match_repo = JobMatchRepository(conn)

    await profile_repo.confirm(profile_id)
    report = await report_repo.create(user_id=user_id, profile_id=profile_id, status="running")
    report_id = report["id"]

    try:
        jobs = fetch_recent_jobs()
        # Over-fetch candidates so link filtering can refill toward top_n
        pool_size = max(settings.top_job_matches * 4, 40)
        candidates = score_jobs(
            jobs,
            profile,
            top_n=pool_size,
            dedupe=True,
            strip_internal=False,
        )
        alive = await filter_alive_apply_links(candidates)
        logger.info(
            "Job pipeline: scored=%s alive=%s target=%s",
            len(candidates),
            len(alive),
            settings.top_job_matches,
        )
        matches = alive[: settings.top_job_matches]
        for m in matches:
            m.pop("_score", None)

        created = await match_repo.bulk_create(report_id, matches)
        json_path, excel_path = write_report_files(
            user_id=user_id,
            report_id=report_id,
            matches=created,
            profile_id=profile_id,
        )
        report = await report_repo.complete(
            report_id,
            json_path=json_path,
            excel_path=excel_path,
            status="ready",
        )
        return {"report": report, "matches": created}
    except Exception:
        await report_repo.set_status(report_id, "failed")
        raise
