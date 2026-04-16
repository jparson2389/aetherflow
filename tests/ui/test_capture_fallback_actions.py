"""Capture diagnostics panel fallback action tests."""

from aetherflow.core.diagnostics import PipelineDiagnostics
from aetherflow.ui.panels.capture_diagnostics_panel import CaptureDiagnosticsPanelModel


def test_capture_diagnostics_panel_surfaces_copy_and_apply_actions() -> None:
    """Diagnostics panel exposes apply_recommendation and copy_diagnostics actions."""
    panel = CaptureDiagnosticsPanelModel(
        recommendation='1080p@60',
        diagnostics_blob='fps=82.0;jitter=6.8',
    )

    assert panel.actions == ['apply_recommendation', 'copy_diagnostics']


def test_capture_diagnostics_panel_from_snapshot() -> None:
    """Panel can be built from a PipelineDiagnostics snapshot."""
    snapshot = PipelineDiagnostics(
        event_rate_hz=120.0,
        output_rate_hz=118.5,
        latency_ms=2.1,
        jitter_ms=0.8,
    )
    panel = CaptureDiagnosticsPanelModel.from_snapshot(
        recommendation='1080p@60',
        snapshot=snapshot,
    )

    assert panel.recommendation == '1080p@60'
    assert panel.metrics['event_rate_hz'] == 120.0
    assert 'event_rate_hz' in panel.diagnostics_blob


def test_capture_diagnostics_panel_recommendation_reflects_input() -> None:
    """The recommendation field reflects whatever was passed in."""
    panel = CaptureDiagnosticsPanelModel(
        recommendation='720p@30',
        diagnostics_blob='{}',
    )
    assert panel.recommendation == '720p@30'


def test_capture_diagnostics_panel_actions_always_present() -> None:
    """Actions are always available regardless of diagnostics content."""
    panel = CaptureDiagnosticsPanelModel(
        recommendation='',
        diagnostics_blob='',
    )
    assert 'apply_recommendation' in panel.actions
    assert 'copy_diagnostics' in panel.actions


def test_capture_diagnostics_panel_metrics_dict_empty_by_default() -> None:
    """Metrics dict is empty when not populated from a snapshot."""
    panel = CaptureDiagnosticsPanelModel(
        recommendation='1080p@60',
        diagnostics_blob='{}',
    )
    assert panel.metrics == {}
