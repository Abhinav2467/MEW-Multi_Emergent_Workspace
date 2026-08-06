import asyncio

import pytest

from resume_parser_agent.dashboard.events import DashboardEventBus


@pytest.mark.asyncio
async def test_event_bus_emits_resume_saved_events() -> None:
    bus = DashboardEventBus()
    subscriber = bus.subscribe()

    next_event = asyncio.create_task(subscriber.__anext__())
    await asyncio.sleep(0)
    await bus.publish_resume_saved(7)
    event = await asyncio.wait_for(next_event, timeout=1)
    await subscriber.aclose()

    assert event == 'data: {"type": "resume_saved", "record_id": 7}\n\n'
