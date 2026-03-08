from aetherflow.ui.panels.driver_status_panel import DriverStatusPanelModel


def test_driver_panel_actions_are_reversible() -> None:
    panel = DriverStatusPanelModel.installed()

    assert panel.actions == ["repair", "disable_masking"]
    assert "reversible" in panel.message
