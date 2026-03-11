from aetherflow.ui.panels.capture_diagnostics_panel import CaptureDiagnosticsPanelModel


def test_capture_diagnostics_panel_surfaces_copy_and_apply_actions() -> None:
    panel = CaptureDiagnosticsPanelModel(
        recommendation='1080p@60',
        diagnostics_blob='fps=82.0;jitter=6.8',
    )

    assert panel.actions == ['apply_recommendation', 'copy_diagnostics']
