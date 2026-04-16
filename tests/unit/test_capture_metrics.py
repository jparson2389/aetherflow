from aetherflow.core.capture_metrics import CaptureMetricsTracker


class FakeClock:
    def __init__(self) -> None:
        self._now = 0.0

    def now(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += seconds


def test_measured_fps_uses_n_minus_one_intervals() -> None:
    """5 frames over 1.0 s spans 4 intervals → 4.0 fps, not 5.0."""
    clock = FakeClock()
    tracker = CaptureMetricsTracker(now=clock.now)

    for i in range(5):
        tracker.record_frame(timestamp_s=float(i) * 0.25)

    snapshot = tracker.snapshot(target_fps=60)

    assert snapshot.measured_fps == 4.0
    assert snapshot.duration_s == 1.0


def test_measured_fps_zero_for_single_frame() -> None:
    """A single frame has no interval → 0 fps."""
    clock = FakeClock()
    tracker = CaptureMetricsTracker(now=clock.now)

    tracker.record_frame(timestamp_s=0.0)

    snapshot = tracker.snapshot(target_fps=60)

    assert snapshot.measured_fps == 0.0
