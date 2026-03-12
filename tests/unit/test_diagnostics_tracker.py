import pytest

from aetherflow.core.diagnostics import PipelineDiagnosticsTracker


class FakeClock:
    def __init__(self) -> None:
        self._now = 0.0

    def now(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += seconds


def test_tracker_reports_rates_latency_and_jitter() -> None:
    clock = FakeClock()
    tracker = PipelineDiagnosticsTracker(window_seconds=5.0, now=clock.now)

    tracker.record_event()
    tracker.record_output()
    tracker.record_latency(10.0)

    clock.advance(1.0)
    tracker.record_event()
    tracker.record_output()
    tracker.record_latency(12.0)

    clock.advance(1.0)
    tracker.record_event()
    tracker.record_latency(8.0)

    snapshot = tracker.snapshot()

    assert snapshot.event_rate_hz == pytest.approx(3 / 5)
    assert snapshot.output_rate_hz == pytest.approx(2 / 5)
    assert snapshot.latency_ms == pytest.approx(10.0)
    assert snapshot.jitter_ms == pytest.approx(4.0)


def test_tracker_prunes_outside_window() -> None:
    clock = FakeClock()
    tracker = PipelineDiagnosticsTracker(window_seconds=5.0, now=clock.now)

    tracker.record_event()
    tracker.record_latency(9.0)

    clock.advance(6.0)
    snapshot = tracker.snapshot()

    assert snapshot.event_rate_hz == 0.0
    assert snapshot.latency_ms == 0.0
    assert snapshot.jitter_ms == 0.0
