"""CareerZenith job board fetcher."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import requests

from backend.config import get_settings


def parse_job_created_at(value: str | None) -> datetime | None:
    """Parse CareerZenith created_at into UTC datetime."""
    if not value or not str(value).strip():
        return None
    text = str(value).strip()
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except ValueError:
        return None


def filter_jobs_within_days(jobs: list[dict[str, Any]], days: int) -> list[dict[str, Any]]:
    """Keep jobs posted within the last `days` days (inclusive of today)."""
    if days <= 0:
        return jobs
    cutoff = datetime.now(UTC) - timedelta(days=days)
    recent: list[dict[str, Any]] = []
    for job in jobs:
        created = parse_job_created_at(job.get("created_at"))
        if created is None:
            continue
        if created >= cutoff:
            recent.append(job)
    return recent


def fetch_all_jobs(timeout: float = 10.0) -> list[dict[str, Any]]:
    settings = get_settings()
    all_jobs: list[dict[str, Any]] = []
    page = 1
    while True:
        url = f"{settings.careerzenith_api_base}?page={page}"
        response = requests.get(url, timeout=timeout)
        if response.status_code != 200:
            break
        data = response.json()
        all_jobs.extend(data.get("jobs", []))
        total_pages = int(data.get("total_pages", page))
        if page >= total_pages:
            break
        page += 1
    return all_jobs


def fetch_recent_jobs(
    *,
    days: int | None = None,
    timeout: float = 10.0,
) -> list[dict[str, Any]]:
    """Fetch jobs and return only those posted within the configured recency window."""
    settings = get_settings()
    window = days if days is not None else settings.job_recency_days
    jobs = fetch_all_jobs(timeout=timeout)
    recent = filter_jobs_within_days(jobs, window)
    recent.sort(
        key=lambda j: parse_job_created_at(j.get("created_at")) or datetime.min.replace(tzinfo=UTC),
        reverse=True,
    )
    return recent
