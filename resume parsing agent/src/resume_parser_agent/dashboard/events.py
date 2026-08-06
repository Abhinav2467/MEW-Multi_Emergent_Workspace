"""Server-sent event support for dashboard live updates."""

from asyncio import Queue
from collections.abc import AsyncIterator
import json


class DashboardEventBus:
    """Small in-process event bus for dashboard refresh events."""

    def __init__(self) -> None:
        self._subscribers: set[Queue[str]] = set()

    async def publish_resume_saved(self, record_id: int) -> None:
        """Publish a resume-saved event to active subscribers."""

        payload = json.dumps({"type": "resume_saved", "record_id": record_id})
        for queue in set(self._subscribers):
            await queue.put(payload)

    async def publish_resume_deleted(self, record_id: int) -> None:
        """Publish a resume-deleted event to active subscribers."""

        payload = json.dumps({"type": "resume_deleted", "record_id": record_id})
        for queue in set(self._subscribers):
            await queue.put(payload)

    async def subscribe(self) -> AsyncIterator[str]:
        """Subscribe to dashboard events as SSE-formatted strings."""

        queue: Queue[str] = Queue()
        self._subscribers.add(queue)
        try:
            while True:
                payload = await queue.get()
                yield f"data: {payload}\n\n"
        finally:
            self._subscribers.discard(queue)
