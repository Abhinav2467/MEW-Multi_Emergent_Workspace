"""Validate job apply links and drop broken URLs."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from backend.config import get_settings

logger = logging.getLogger(__name__)

BROKEN_STATUS_CODES = {404, 410, 451}


async def _check_one(
    client: httpx.AsyncClient,
    url: str,
    semaphore: asyncio.Semaphore,
) -> bool:
    """Return True if the URL looks alive."""
    if not url or not url.startswith(("http://", "https://")):
        return False

    async with semaphore:
        try:
            resp = await client.head(url)
            # Some boards reject HEAD
            if resp.status_code in {405, 403, 400} or resp.status_code >= 500:
                resp = await client.get(url)
            status = resp.status_code
            if status in BROKEN_STATUS_CODES or status >= 500:
                return False
            return 200 <= status < 400
        except Exception as exc:
            logger.debug("Link check failed for %s: %s", url, exc)
            return False


async def filter_alive_apply_links(
    jobs: list[dict[str, Any]],
    *,
    concurrency: int | None = None,
    timeout: float | None = None,
) -> list[dict[str, Any]]:
    """Keep jobs whose apply_link responds successfully."""
    if not jobs:
        return []

    settings = get_settings()
    concurrency = concurrency if concurrency is not None else settings.link_check_concurrency
    timeout = timeout if timeout is not None else settings.link_check_timeout_seconds
    semaphore = asyncio.Semaphore(max(1, concurrency))

    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=timeout,
        limits=limits,
        headers={"User-Agent": "JobApplyingAgentLinkChecker/1.0"},
    ) as client:
        results = await asyncio.gather(
            *[_check_one(client, job.get("apply_link") or "", semaphore) for job in jobs]
        )

    alive = [job for job, ok in zip(jobs, results) if ok]
    dropped = len(jobs) - len(alive)
    if dropped:
        logger.info("Dropped %s jobs with broken apply links", dropped)
    return alive


def filter_alive_apply_links_sync(jobs: list[dict[str, Any]], **kwargs: Any) -> list[dict[str, Any]]:
    """Sync wrapper for callers that are not async."""
    return asyncio.run(filter_alive_apply_links(jobs, **kwargs))
