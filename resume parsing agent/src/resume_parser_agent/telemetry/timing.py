"""Timing utilities for parser stages."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from time import perf_counter


@dataclass(frozen=True, slots=True)
class TimingRecord:
    """Single stage timing measurement in milliseconds."""

    stage: str
    elapsed_ms: float


@dataclass(slots=True)
class ParseTiming:
    """Container for parser stage timing measurements."""

    records: list[TimingRecord] = field(default_factory=list)

    def add(self, stage: str, elapsed_ms: float) -> None:
        """Record one stage duration."""

        if not stage:
            raise ValueError("stage name is required")
        if elapsed_ms < 0:
            raise ValueError("elapsed_ms cannot be negative")
        self.records.append(TimingRecord(stage=stage, elapsed_ms=elapsed_ms))

    @property
    def total_ms(self) -> float:
        """Return the sum of recorded stage durations."""

        return sum(record.elapsed_ms for record in self.records)

    def as_dict(self) -> dict[str, float]:
        """Return stage timings keyed by stage name."""

        return {record.stage: record.elapsed_ms for record in self.records}

    def is_within_budget(self, budget_ms: int | float) -> bool:
        """Return whether total recorded time is within the configured budget."""

        if budget_ms <= 0:
            raise ValueError("budget_ms must be positive")
        return self.total_ms <= budget_ms


@contextmanager
def time_stage(stage: str, timing: ParseTiming) -> Iterator[None]:
    """Measure a stage and append the duration to a ParseTiming instance."""

    start = perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (perf_counter() - start) * 1000
        timing.add(stage, elapsed_ms)
