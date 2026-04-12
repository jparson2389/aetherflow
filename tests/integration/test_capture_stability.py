from aetherflow.core.capture_metrics import CaptureMetrics, CaptureMetricsTracker


def test_capture_metrics_flag_instability_and_offer_fallback() -> None:
    metrics = CaptureMetrics(
        target_fps=120,
        measured_fps=82.0,
        dropped_frames=12,
        jitter_ms=6.8,
    )

    assert metrics.is_stable is False
    assert metrics.recommended_fallback() == '1080p@60'


def test_capture_metrics_flags_sustained_drop_by_fps() -> None:
    metrics = CaptureMetrics(
        target_fps=60,
        measured_fps=50.0,
        dropped_frames=1,
        jitter_ms=1.0,
        duration_s=3.5,
        frames_total=200,
        drop_window_s=5.0,
    )

    assert metrics.is_sustained_drop is True


def test_capture_metrics_flags_sustained_drop_by_drop_rate() -> None:
    metrics = CaptureMetrics(
        target_fps=60,
        measured_fps=60.0,
        dropped_frames=10,
        jitter_ms=1.0,
        duration_s=2.0,
        frames_total=300,
        drop_window_s=5.0,
    )

    assert metrics.is_sustained_drop is True


def test_capture_metrics_tracker_measures_60fps_baseline() -> None:
    tracker = CaptureMetricsTracker(window_seconds=5.0, now=lambda: 1.0)

    for index in range(60):
        tracker.record_frame(timestamp_s=index / 60.0)

    metrics = tracker.snapshot(target_fps=60)

    assert metrics.target_fps == 60
    assert metrics.measured_fps >= 60.0
    assert metrics.is_sustained_drop is False


def test_capture_metrics_tracker_detects_sustained_drop_from_samples() -> None:
    tracker = CaptureMetricsTracker(window_seconds=5.0, now=lambda: 3.5)

    for index in range(175):
        tracker.record_frame(timestamp_s=index * 0.02)

    metrics = tracker.snapshot(target_fps=60)

    assert metrics.measured_fps < 54.0
    assert metrics.duration_s >= 3.0
    assert metrics.is_sustained_drop is True
