import pytest

from resume_parser_agent.bot.session_store import SessionState, SessionStore


@pytest.mark.asyncio
async def test_session_store_get_set_and_clear() -> None:
    store = SessionStore()

    session = await store.get(123)
    session.state = SessionState.AWAITING_CONFIRMATION
    await store.set(session)

    assert (await store.get(123)).state == SessionState.AWAITING_CONFIRMATION

    await store.clear(123)

    assert (await store.get(123)).state == SessionState.IDLE
