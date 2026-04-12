"""Tests for Phase 1 Qt widgets: AppWindow, HudWidget, PanelHost."""

from __future__ import annotations

import sys

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != 'win32',
    reason='Qt widget tests run on Windows only',
)


@pytest.fixture(scope='module')
def _qt_app():
    """Provide a single QApplication instance for the module."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv[:1])
    yield app


class FakeCaptureProbe:
    def enumerate_devices(self):
        from aetherflow.vision.opencv_capture import CaptureDevice

        return [
            CaptureDevice(
                stable_id='capture-usb-vid-0fd9-pid-00af-mi-00',
                name='Elgato 4K S',
                device_id='USB\\VID_0FD9&PID_00AF&MI_00\\9&27FBDE15&0&0000',
                backend_index=0,
            )
        ]

    def supported_modes(self, device):
        from aetherflow.vision.opencv_capture import CaptureMode

        if device.stable_id != 'capture-usb-vid-0fd9-pid-00af-mi-00':
            return []
        return [
            CaptureMode(1920, 1080, 60, 'NV12', 'BGR', False, True, 'USB-C 3.2'),
            CaptureMode(1920, 1080, 120, 'NV12', 'BGR', False, False, 'USB-C 3.2'),
            CaptureMode(3840, 2160, 60, 'MJPEG', 'BGR', False, False, 'USB-C 3.2'),
        ]


class TestHudWidget:
    """HudWidget renders StatusHUDModel data as Qt labels."""

    def test_hud_widget_shows_runtime_state(self, _qt_app) -> None:
        from aetherflow.core.entitlements import EntitlementState
        from aetherflow.core.runtime_state import RuntimeState
        from aetherflow.ui.hud_widget import HudWidget
        from aetherflow.ui.status_hud import StatusHUDModel

        model = StatusHUDModel(
            input_plugin='xinput',
            output_plugin='vigem',
            capture_plugin='capture.opencv',
            display_plugin='render.cpu',
            measured_fps=60.0,
            jitter_ms=2.0,
            worker_health=RuntimeState.RUNNING,
            entitlement_state=EntitlementState.LOADED,
            runtime_state=RuntimeState.RUNNING,
        )
        widget = HudWidget(model)

        assert 'RUNNING' in widget.runtime_state_text()

    def test_hud_widget_shows_fps(self, _qt_app) -> None:
        from aetherflow.core.entitlements import EntitlementState
        from aetherflow.core.runtime_state import RuntimeState
        from aetherflow.ui.hud_widget import HudWidget
        from aetherflow.ui.status_hud import StatusHUDModel

        model = StatusHUDModel(
            input_plugin='xinput',
            output_plugin='vigem',
            capture_plugin='capture.opencv',
            display_plugin='render.cpu',
            measured_fps=120.0,
            jitter_ms=1.0,
            worker_health=RuntimeState.RUNNING,
            entitlement_state=EntitlementState.LOADED,
            runtime_state=RuntimeState.RUNNING,
        )
        widget = HudWidget(model)

        assert '120' in widget.fps_text()

    def test_hud_widget_shows_degraded_state(self, _qt_app) -> None:
        from aetherflow.core.entitlements import EntitlementState
        from aetherflow.core.runtime_state import RuntimeState
        from aetherflow.ui.hud_widget import HudWidget
        from aetherflow.ui.status_hud import StatusHUDModel

        model = StatusHUDModel(
            input_plugin='xinput',
            output_plugin='vigem',
            capture_plugin='capture.opencv',
            display_plugin='render.cpu',
            measured_fps=0.0,
            jitter_ms=0.0,
            worker_health=RuntimeState.DEGRADED,
            entitlement_state=EntitlementState.GRACE,
            runtime_state=RuntimeState.DEGRADED,
        )
        widget = HudWidget(model)

        assert 'DEGRADED' in widget.runtime_state_text()


class TestPanelHost:
    """PanelHost switches between panels based on RouterModel."""

    def test_panel_host_starts_empty(self, _qt_app) -> None:
        from aetherflow.ui.panel_host import PanelHost
        from aetherflow.ui.router import RouterModel

        router = RouterModel()
        host = PanelHost(router)

        assert host.current_panel_id() is None

    def test_panel_host_switches_to_registered_panel(self, _qt_app) -> None:
        from PySide6.QtWidgets import QLabel

        from aetherflow.ui.panel_host import PanelHost
        from aetherflow.ui.router import RouteDefinition, RouterModel

        router = RouterModel()
        router.register_route(
            RouteDefinition(
                name='dashboard', title='Dashboard', panel_id='panel.dashboard'
            )
        )
        host = PanelHost(router)
        placeholder = QLabel('Dashboard panel')
        host.register_panel('panel.dashboard', placeholder)

        host.show_panel('panel.dashboard')

        assert host.current_panel_id() == 'panel.dashboard'

    def test_panel_host_unknown_panel_raises(self, _qt_app) -> None:
        from aetherflow.ui.panel_host import PanelHost
        from aetherflow.ui.router import RouterModel

        router = RouterModel()
        host = PanelHost(router)

        with pytest.raises(KeyError):
            host.show_panel('panel.unknown')


class TestAppWindow:
    """AppWindow is the QMainWindow that hosts the full UI."""

    def test_app_window_title_matches_shell(self, _qt_app) -> None:
        from aetherflow.ui.app_window import AppWindow
        from aetherflow.ui.shell import ShellModel

        shell = ShellModel(title='Aetherflow')
        window = AppWindow(shell)

        assert window.windowTitle() == 'Aetherflow'

    def test_app_window_has_hud_widget(self, _qt_app) -> None:
        from aetherflow.ui.app_window import AppWindow
        from aetherflow.ui.hud_widget import HudWidget
        from aetherflow.ui.shell import ShellModel

        shell = ShellModel()
        window = AppWindow(shell)

        assert window.hud_widget is not None
        assert isinstance(window.hud_widget, HudWidget)

    def test_app_window_has_panel_host(self, _qt_app) -> None:
        from aetherflow.ui.app_window import AppWindow
        from aetherflow.ui.panel_host import PanelHost
        from aetherflow.ui.shell import ShellModel

        shell = ShellModel()
        window = AppWindow(shell)

        assert window.panel_host is not None
        assert isinstance(window.panel_host, PanelHost)

    def test_app_window_starts_with_empty_placeholder_panel(self, _qt_app) -> None:
        from aetherflow.ui.app_window import EMPTY_PANEL_ID, AppWindow
        from aetherflow.ui.shell import ShellModel

        shell = ShellModel()
        window = AppWindow(shell)

        assert window.panel_host.current_panel_id() == EMPTY_PANEL_ID

    def test_app_window_syncs_active_shell_route(self, _qt_app) -> None:
        from aetherflow.ui.app_window import AppWindow
        from aetherflow.ui.bootstrap import configure_default_shell
        from aetherflow.ui.shell import ShellModel

        shell = configure_default_shell(ShellModel())
        window = AppWindow(shell)

        assert window.panel_host.current_panel_id() == 'panel.home'
        assert window.route_list.count() == 5

    def test_app_window_capture_panel_renders_live_probe_data(self, _qt_app) -> None:
        from aetherflow.ui.app_window import AppWindow
        from aetherflow.ui.bootstrap import configure_default_shell
        from aetherflow.ui.shell import ShellModel
        from aetherflow.vision.opencv_capture import OpenCVCapturePlugin

        shell = configure_default_shell(ShellModel())
        window = AppWindow(
            shell, capture_plugin=OpenCVCapturePlugin(probe=FakeCaptureProbe())
        )

        window.navigate_to('capture')

        assert window.panel_host.current_panel_id() == 'panel.capture'
        assert window.capture_panel is not None
        assert window.capture_panel.device_list.count() == 1
        assert 'Elgato 4K S' in window.capture_panel.device_list.item(0).text()
        assert 'VID_0FD9&PID_00AF' in window.capture_panel.device_details_label.text()
        assert window.capture_panel.mode_list.count() == 3
        assert '1920x1080 @ 120 FPS' in window.capture_panel.mode_list.item(1).text()
        assert 'HDR' in window.capture_panel.mode_list.item(0).text()

    def test_app_window_shows_without_crashing(self, _qt_app) -> None:
        from aetherflow.ui.app_window import AppWindow
        from aetherflow.ui.shell import ShellModel

        shell = ShellModel()
        window = AppWindow(shell)
        window.show()
        window.hide()
        window.close()
