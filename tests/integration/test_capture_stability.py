from aetherflow.core.capture_metrics import CaptureMetrics


def test_capture_metrics_flag_instability_and_offer_fallback() -> None:
    metrics = CaptureMetrics(
        target_fps=120,
        measured_fps=82.0,
        dropped_frames=12,
        jitter_ms=6.8,
    )

    assert metrics.is_stable is False
    assert metrics.recommended_fallback() == "1080p@60"
