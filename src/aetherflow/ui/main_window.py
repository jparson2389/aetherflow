"""PySide6 implementation of the Aetherflow main window."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from aetherflow.ui.shell import ShellModel


class StatusHUDWidget(QWidget):
    """Always-visible status HUD at the top of the shell."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the HUD with a dark theme."""
        super().__init__(parent)
        self.setFixedHeight(40)
        self.setStyleSheet(
            'background-color: #1a1a2e; border-bottom: 2px solid #000000; color: #e1e1e1;'
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)

        # Telemetry Labels
        self.fps_label = QLabel('FPS: 0.0')
        self.jitter_label = QLabel('Jitter: 0.0ms')
        self.state_label = QLabel('State: RUNNING')
        self.entitlement_label = QLabel('Entitlement: LOADED')

        # Style labels
        for label in (self.fps_label, self.jitter_label, self.state_label, self.entitlement_label):
            label.setStyleSheet('font-weight: bold; margin-right: 15px;')

        layout.addWidget(self.fps_label)
        layout.addWidget(self.jitter_label)
        layout.addStretch()
        layout.addWidget(self.entitlement_label)
        layout.addWidget(self.state_label)

    def update_from_model(self, model: ShellModel) -> None:
        """Update the HUD labels from the shell model data."""
        if not model.status_hud:
            return

        hud = model.status_hud
        self.fps_label.setText(f'FPS: {hud.measured_fps:.1f}')
        self.jitter_label.setText(f'Jitter: {hud.jitter_ms:.1f}ms')
        self.state_label.setText(f'State: {hud.runtime_state.value}')
        self.entitlement_label.setText(f'Entitlement: {hud.entitlement_state.value}')

        # Color-code based on state
        if hud.runtime_state.value != 'RUNNING':
            self.state_label.setStyleSheet('color: #f1c40f; font-weight: bold;')
        else:
            self.state_label.setStyleSheet('color: #2ecc71; font-weight: bold;')


class MainWindow(QMainWindow):
    """The primary Aetherflow shell window."""

    def __init__(self, model: ShellModel) -> None:
        """Initialize the main window with the provided shell model."""
        super().__init__()
        self.model = model
        self.setWindowTitle(model.title)
        self.setMinimumSize(1024, 768)

        # View lookup
        self.panels: dict[str, QWidget] = {}

        # Apply dark theme
        self.setStyleSheet(
            'QMainWindow { background-color: #0f0f1b; }'
            'QWidget { color: #e1e1e1; font-family: "Segoe UI", sans-serif; }'
        )

        # Main Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Add Status HUD
        self.status_hud = StatusHUDWidget()
        self.main_layout.addWidget(self.status_hud)

        # Content Area
        self.content_layout = QHBoxLayout()
        self.main_layout.addLayout(self.content_layout)

        # Sidebar (Navigation)
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(200)
        self.sidebar.setStyleSheet('background-color: #161625; border-right: 1px solid #2e2e42;')
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.content_layout.addWidget(self.sidebar)

        # Feature Panel Container
        self.panel_stack = QStackedWidget()
        self.content_layout.addWidget(self.panel_stack)

        self._build_navigation()
        self._refresh_ui()

    def _build_navigation(self) -> None:
        """Create navigation buttons based on available routes."""
        # Clear existing buttons
        for i in reversed(range(self.sidebar_layout.count())):
            item = self.sidebar_layout.itemAt(i)
            if item and item.widget():
                item.widget().setParent(None)

        # Add buttons for each route
        for route in self.model.router.available_routes():
            btn = QPushButton(route.title)
            btn.setFixedHeight(40)
            btn.setStyleSheet(
                'QPushButton { background-color: transparent; border: none; text-align: left; padding-left: 15px; }'
                'QPushButton:hover { background-color: #2e2e42; }'
                'QPushButton:checked { border-left: 3px solid #000000; background-color: #252538; }'
            )
            btn.setCheckable(True)
            if route.name == self.model.router.active_route:
                btn.setChecked(True)

            btn.clicked.connect(lambda checked, r=route.name: self._handle_navigation(r))
            self.sidebar_layout.addWidget(btn)

    @Slot(str)
    def _handle_navigation(self, route_name: str) -> None:
        """Handle navigation requests from the sidebar."""
        try:
            self.model.set_active_route(route_name, role=None)
            self._build_navigation()  # Refresh button check states
            self._refresh_ui()
        except Exception as e:
            self.model.record_route_failure(route_name, reason=str(e))

    def _refresh_ui(self) -> None:
        """Update all UI elements from the model state."""
        self.status_hud.update_from_model(self.model)
        
        panel_id = self.model.active_panel_id()
        if not panel_id:
            return

        # Lazy-load panel views
        if panel_id not in self.panels:
            view = self._create_panel_view(panel_id)
            if view:
                self.panels[panel_id] = view
                self.panel_stack.addWidget(view)

        # Switch to the active panel and update with mock data for now
        if panel_id in self.panels:
            self.panel_stack.setCurrentWidget(self.panels[panel_id])
            view = self.panels[panel_id]
            if hasattr(view, 'update_from_model'):
                if panel_id == 'panel.catalog':
                    from aetherflow.plugins.catalog import (
                        CatalogEntry,
                        CatalogLockState,
                        PluginType,
                    )
                    from aetherflow.ui.panels.plugin_catalog_panel import (
                        PluginCatalogPanelModel,
                    )
                    mock_model = PluginCatalogPanelModel(
                        entries=[
                            CatalogEntry(
                                plugin_id='cap.v1', name='Base Capture', version='1.0.0', 
                                api_version='1.0', plugin_type=PluginType.CAPTURE, 
                                lock_state=CatalogLockState.AVAILABLE
                            ),
                            CatalogEntry(
                                plugin_id='cap.v2', name='Premium Capture', version='1.1.0', 
                                api_version='1.0', plugin_type=PluginType.CAPTURE, 
                                lock_state=CatalogLockState.LOCKED
                            ),
                        ],
                        available_count=1,
                        locked_count=1,
                        grace_count=0
                    )
                    view.update_from_model(mock_model)
                elif panel_id == 'panel.environment':
                    from aetherflow.core.env_manager import GpuProbeStatus
                    from aetherflow.ui.panels.environment_panel import (
                        EnvironmentPanelModel,
                        EnvironmentSummary,
                    )
                    mock_model = EnvironmentPanelModel(
                        environments=[
                            EnvironmentSummary(
                                name='default', python_version='3.12.2', dependency_count=15, 
                                validation_status='valid', gpu_probe_status=GpuProbeStatus.SUPPORTED
                            ),
                            EnvironmentSummary(
                                name='vision-test', python_version='3.12.2', dependency_count=42, 
                                validation_status='failed', gpu_probe_status=GpuProbeStatus.ERROR,
                                missing_imports=['cv2', 'torch']
                            ),
                        ],
                        failed_count=1,
                        pending_count=0
                    )
                    view.update_from_model(mock_model)

    def _create_panel_view(self, panel_id: str) -> QWidget | None:
        """Create a view instance for a given panel identifier."""
        if panel_id == 'panel.catalog':
            from aetherflow.ui.panels.plugin_catalog_view import PluginCatalogView
            return PluginCatalogView()
        if panel_id == 'panel.environment':
            from aetherflow.ui.panels.environment_view import EnvironmentView
            return EnvironmentView()
        # Add other panels as they are implemented
        return None

    def closeEvent(self, event) -> None:
        """Shut down the shell model when the window is closed."""
        self.model.shutdown()
        event.accept()


def run_app(model: ShellModel) -> int:
    """Launch the PySide6 application loop."""
    app = QApplication(sys.argv)
    window = MainWindow(model)
    window.show()
    return app.exec()
