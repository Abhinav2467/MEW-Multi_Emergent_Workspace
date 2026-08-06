from time import sleep

import pytest

from resume_parser_agent.telemetry.timing import ParseTiming, time_stage


def test_time_stage_records_elapsed_time() -> None:
    timing = ParseTiming()

    with time_stage("extract", timing):
        sleep(0.001)

    assert len(timing.records) == 1
    assert timing.records[0].stage == "extract"
    assert timing.records[0].elapsed_ms > 0


def test_parse_timing_returns_total_and_dict() -> None:
    timing = ParseTiming()
    timing.add("extract", 10.5)
    timing.add("parse", 20.0)

    assert timing.total_ms == 30.5
    assert timing.as_dict() == {"extract": 10.5, "parse": 20.0}
    assert timing.is_within_budget(300)


def test_parse_timing_rejects_invalid_values() -> None:
    timing = ParseTiming()

    with pytest.raises(ValueError, match="stage name is required"):
        timing.add("", 1)

    with pytest.raises(ValueError, match="elapsed_ms cannot be negative"):
        timing.add("extract", -1)

    with pytest.raises(ValueError, match="budget_ms must be positive"):
        timing.is_within_budget(0)
