import sys

import pytest

from aetherflow.core.runtime_state import RuntimeState
from aetherflow.output.device_masking import DeviceMaskingService
from aetherflow.output.virtual_controller import VirtualControllerService
from aetherflow.ui.panels.driver_status_panel import DriverStatusPanelModel


def test_driver_panel_actions_are_reversible() -> None:
    panel = DriverStatusPanelModel.for_installed_driver()

    assert panel.masking_enabled is True
    assert panel.actions == ['repair', 'disable_masking']
    assert 'reversible' in panel.message


def test_driver_panel_marks_failure_state() -> None:
    panel = DriverStatusPanelModel.for_failed_driver()

    assert panel.installed is False
    assert panel.diagnostics_available is True
    assert 'repair' in panel.actions
    assert 'failed' in panel.message.lower()


def test_driver_panel_reflects_live_service_state() -> None:
    service = VirtualControllerService(masking_service=DeviceMaskingService())
    service.install_driver()
    service.enable_masking()

    panel = DriverStatusPanelModel.from_service(service)

    assert panel.installed is True
    assert panel.masking_enabled is True
    assert panel.actions == ['repair', 'disable_masking']
    assert panel.runtime_state is RuntimeState.RUNNING


def test_driver_panel_surfaces_masking_failure() -> None:
    def apply_state(_target) -> None:
        raise RuntimeError('driver masking failure surfaced')

    service = VirtualControllerService(
        masking_service=DeviceMaskingService(apply_state=apply_state)
    )
    service.install_driver()
    service.enable_masking()

    panel = DriverStatusPanelModel.from_service(service)

    assert panel.runtime_state is RuntimeState.DEGRADED
    assert panel.failure_reason == 'driver masking failure surfaced'
    assert panel.diagnostics_available is True
    assert 'retry_masking' in panel.actions


# ── UI wiring tests (Windows + Qt required) ──────────────────────────────────


@pytest.fixture(scope='module')
def _qt_app():
    """Provide a single QApplication instance for the module."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv[:1])
    yield app


@pytest.mark.skipif(
    sys.platform != 'win32', reason='Qt widget tests run on Windows only'
)
class TestDriverStatusPanelWiring:
    """Verify VirtualControllerService is wired into the live app path."""

    def test_driver_status_panel_reachable_via_bootstrap_path(self, _qt_app) -> None:
        """3.1 — panel/model is reachable from the same path main.py uses."""
        from aetherflow.ui.app_window import AppWindow, DriverStatusPanelWidget
        from aetherflow.ui.bootstrap import configure_default_shell
        from aetherflow.ui.shell import ShellModel

        shell = configure_default_shell(ShellModel())
        window = AppWindow(shell)

        # Panel must be mounted and navigable through the production route
        assert isinstance(window.driver_status_panel, DriverStatusPanelWidget)
        window.navigate_to('output')
        assert window.panel_host.current_panel_id() == 'panel.output'

        # DriverStatusPanelModel must be obtainable via the production service
        model = DriverStatusPanelModel.from_service(window.driver_status_panel._service)
        assert model is not None

    def test_virtual_controller_service_registered_in_app_window(self, _qt_app) -> None:
        """3.2 — VirtualControllerService is live in AppWindow; panel actions reach it."""
        from aetherflow.ui.app_window import AppWindow, DriverStatusPanelWidget
        from aetherflow.ui.shell import ShellModel

        svc = VirtualControllerService(masking_service=DeviceMaskingService())
        window = AppWindow(ShellModel(), virtual_controller_service=svc)

        # Service must be the injected instance, not a detached default
        assert isinstance(window.driver_status_panel, DriverStatusPanelWidget)
        assert window.driver_status_panel._service is svc

        # Panel install button routes through to the service
        assert svc.status()['driver_installed'] is False
        window.driver_status_panel.install_btn.click()
        assert svc.status()['driver_installed'] is True
