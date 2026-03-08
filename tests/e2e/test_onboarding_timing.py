from aetherflow.core.diagnostics_export import SuccessMetrics


def test_onboarding_metric_tracks_target_threshold() -> None:
    metrics = SuccessMetrics()
    metrics.record_onboarding_time(240)

    assert metrics.onboarding_within_target(target_seconds=300) is True
