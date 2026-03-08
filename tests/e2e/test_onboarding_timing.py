from pathlib import Path

from aetherflow.core.diagnostics_export import SuccessMetrics


def test_onboarding_metric_tracks_target_threshold() -> None:
    metrics = SuccessMetrics()
    metrics.record_onboarding_time(240)

    assert metrics.onboarding_within_target(target_seconds=300) is True


def test_onboarding_metric_exports_report(tmp_path: Path) -> None:
    metrics = SuccessMetrics()
    metrics.record_onboarding_time(240)

    report_path = tmp_path / "onboarding_timing.json"
    metrics.export_onboarding_report(report_path)

    assert report_path.exists()
