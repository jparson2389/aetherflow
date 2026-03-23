"""Tests for Phase 1 Qt widgets: AppWindow, HudWidget, PanelHost."""

from __future__ import annotations

import sys

import pytest


@pytest.fixture(scope='module')
def _qt_app():
    """Provide a single QApplication instance for the module."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv[:1])
    yield app


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
            RouteDefinition(name='dashboard', title='Dashboard', panel_id='panel.dashboard')
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

    def test_app_window_shows_without_crashing(self, _qt_app) -> None:
        from aetherflow.ui.app_window import AppWindow
        from aetherflow.ui.shell import ShellModel

        shell = ShellModel()
        window = AppWindow(shell)
        window.show()
        window.hide()
        window.close()
