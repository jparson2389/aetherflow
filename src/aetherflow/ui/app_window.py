"""Main application window — industrial dark / gaming HUD aesthetic."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from aetherflow.core.entitlements import EntitlementState, RoleName
from aetherflow.output.device_masking import DeviceMaskingService
from aetherflow.output.virtual_controller import VirtualControllerService
from aetherflow.ui.hud_widget import HudWidget
from aetherflow.ui.panel_host import PanelHost
from aetherflow.ui.panels.driver_status_panel import DriverStatusPanelModel
from aetherflow.ui.shell import ShellModel
from aetherflow.ui.status_hud import StatusHUDModel
from aetherflow.vision.opencv_capture import (
    CaptureDevice,
    CaptureMode,
    OpenCVCapturePlugin,
)

# ── Palette ───────────────────────────────────────────────────────────────────
_BG_DEEP = '#0a0c0f'
_BG = '#0f1114'
_BG_PANEL = '#13161b'
_BORDER = '#1e2229'
_AMBER = '#f5a623'
_TEXT_DIM = '#4a5568'
_TEXT = '#c8d0dc'
_TEXT_BRIGHT = '#e8edf5'

_APP_QSS = f"""
QMainWindow, QWidget {{
    background-color: {_BG};
    color: {_TEXT};
    font-family: "Segoe UI", "SF Pro Display", system-ui;
}}
QMainWindow::separator {{
    background: {_BORDER};
    width: 1px;
    height: 1px;
}}
"""

_TITLE_BAR_QSS = f"""
QWidget#title_bar {{
    background-color: {_BG_DEEP};
    border-bottom: 1px solid {_BORDER};
}}
QLabel#app_title {{
    color: {_AMBER};
    font-family: "Consolas", "Courier New", monospace;
    font-size: 13px;
    font-weight: bold;
    letter-spacing: 3px;
}}
QLabel#app_subtitle {{
    color: {_TEXT_DIM};
    font-family: "Consolas", monospace;
    font-size: 9px;
    letter-spacing: 2px;
}}
"""

_CONTENT_QSS = f"""
QWidget#content_area {{
    background-color: {_BG_PANEL};
    border: 1px solid {_BORDER};
    margin: 8px;
}}
QLabel#placeholder {{
    color: {_TEXT_DIM};
    font-family: "Consolas", monospace;
    font-size: 11px;
    letter-spacing: 1px;
}}
"""

_ROUTE_RAIL_QSS = f"""
QListWidget#route_list {{
    background-color: {_BG_DEEP};
    border-right: 1px solid {_BORDER};
    color: {_TEXT};
    min-width: 176px;
}}
QListWidget#route_list::item {{
    padding: 10px 12px;
    border-bottom: 1px solid {_BORDER};
}}
QListWidget#route_list::item:selected {{
    background-color: {_BG_PANEL};
    color: {_AMBER};
}}
"""

# Reserved panel id for the empty-state view (no plugin panel loaded yet).
EMPTY_PANEL_ID = 'panel.empty'


def _default_hud_model(shell: ShellModel) -> StatusHUDModel:
    """Build a startup HUD model from shell state when no explicit model is set."""
    return StatusHUDModel(
        input_plugin='—',
        output_plugin='—',
        capture_plugin='—',
        display_plugin='—',
        measured_fps=0.0,
        jitter_ms=0.0,
        worker_health=shell.runtime_state,
        entitlement_state=EntitlementState.LOADED,
        runtime_state=shell.runtime_state,
    )


def _build_title_bar(title: str) -> QWidget:
    """Create the branded title bar widget."""
    bar = QWidget()
    bar.setObjectName('title_bar')
    bar.setFixedHeight(36)
    bar.setStyleSheet(_TITLE_BAR_QSS)

    layout = QHBoxLayout(bar)
    layout.setContentsMargins(12, 0, 12, 0)
    layout.setSpacing(8)

    # Diamond mark
    mark = QLabel('◆')
    mark.setStyleSheet(f'color: {_AMBER}; font-size: 10px; background: transparent;')

    title_lbl = QLabel(title.upper())
    title_lbl.setObjectName('app_title')

    sub_lbl = QLabel('CONTROLLER ADAPTER HOST')
    sub_lbl.setObjectName('app_subtitle')

    layout.addWidget(mark)
    layout.addWidget(title_lbl)
    layout.addSpacing(6)
    layout.addWidget(sub_lbl)
    layout.addStretch()

    return bar


def _build_placeholder_content() -> QWidget:
    """Build placeholder content area shown before any panel is loaded."""
    wrapper = QWidget()
    wrapper.setObjectName('content_area')
    wrapper.setStyleSheet(_CONTENT_QSS)

    layout = QVBoxLayout(wrapper)
    lbl = QLabel('// NO PANEL LOADED')
    lbl.setObjectName('placeholder')
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(lbl)

    return wrapper


def _build_route_placeholder(*, title: str, body: str) -> QWidget:
    """Build a generic route placeholder panel."""
    wrapper = QWidget()
    wrapper.setObjectName('content_area')
    wrapper.setStyleSheet(_CONTENT_QSS)

    layout = QVBoxLayout(wrapper)
    title_label = QLabel(title)
    title_label.setObjectName('app_title')
    body_label = QLabel(body)
    body_label.setObjectName('placeholder')
    body_label.setWordWrap(True)
    layout.addWidget(title_label)
    layout.addWidget(body_label)
    layout.addStretch()
    return wrapper


class CapturePanelWidget(QWidget):
    """Capture panel widget backed by the OpenCV capture plugin."""

    def __init__(
        self,
        plugin: OpenCVCapturePlugin,
        parent: QWidget | None = None,
    ) -> None:
        """Create the capture panel widget.

        Args:
            plugin: Capture plugin used for live device enumeration.
            parent: Optional Qt parent.

        """
        super().__init__(parent)
        self._plugin = plugin
        self._cached_devices: list[CaptureDevice] = []
        self.summary_label = QLabel()
        self.device_details_label = QLabel()
        self.device_details_label.setWordWrap(True)
        self.device_list = QListWidget()
        self.mode_list = QListWidget()

        wrapper = QWidget(self)
        wrapper.setObjectName('content_area')
        wrapper.setStyleSheet(_CONTENT_QSS)

        layout = QVBoxLayout(wrapper)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.device_details_label)
        layout.addWidget(self.device_list)
        layout.addWidget(self.mode_list)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.addWidget(wrapper)

        self.device_list.currentRowChanged.connect(self._on_device_selected)
        self.refresh()

    def refresh(self) -> None:
        """Refresh the device and mode lists from the plugin."""
        devices = self._plugin.enumerate_devices()
        self._cached_devices = list(devices)
        self.device_list.clear()
        self.mode_list.clear()
        if not devices:
            self.summary_label.setText('No capture devices detected.')
            self.device_details_label.setText(
                'Connect a capture card and restart probing.'
            )
            return

        self.summary_label.setText(f'{len(devices)} capture device(s) detected')
        for device in devices:
            item = QListWidgetItem(device.name)
            item.setData(Qt.ItemDataRole.UserRole, device.stable_id)
            self.device_list.addItem(item)
        self.device_list.setCurrentRow(0)

    def _on_device_selected(self, row: int) -> None:
        """Update details and modes for the selected device."""
        if row < 0:
            self.device_details_label.setText('')
            self.mode_list.clear()
            return
        item = self.device_list.item(row)
        stable_id = item.data(Qt.ItemDataRole.UserRole)
        device = next(
            (
                candidate
                for candidate in self._cached_devices
                if candidate.stable_id == stable_id
            ),
            None,
        )
        if device is None:
            self.device_details_label.setText('Selected device is no longer available.')
            self.mode_list.clear()
            return

        self.device_details_label.setText(
            f'Device ID: {device.device_id}\nStable ID: {device.stable_id}'
        )
        self.mode_list.clear()
        for mode in self._plugin.supported_modes(device.stable_id):
            self.mode_list.addItem(QListWidgetItem(_format_capture_mode(mode)))


def _format_capture_mode(mode: CaptureMode) -> str:
    """Return human-readable text for one capture mode."""
    hdr_suffix = ' HDR' if mode.hdr_supported else ''
    return (
        f'{mode.capture_width}x{mode.capture_height} @ {mode.capture_fps} FPS'
        f'{hdr_suffix} [{mode.pixel_format_in}]'
    )


class DriverStatusPanelWidget(QWidget):
    """Driver status panel widget backed by the virtual controller service."""

    def __init__(
        self,
        service: VirtualControllerService,
        parent: QWidget | None = None,
    ) -> None:
        """Create the driver status panel widget.

        Args:
            service: Virtual controller service powering the panel.
            parent: Optional Qt parent.

        """
        super().__init__(parent)
        self._service = service

        self.status_label = QLabel()
        self.message_label = QLabel()
        self.message_label.setWordWrap(True)
        self.failure_label = QLabel()
        self.failure_label.setWordWrap(True)
        self.install_btn = QPushButton('Install Driver')
        self.repair_btn = QPushButton('Repair Driver')
        self.retry_masking_btn = QPushButton('Retry Masking')
        self.enable_masking_btn = QPushButton('Enable Masking')
        self.disable_masking_btn = QPushButton('Disable Masking')
        self.copy_diagnostics_btn = QPushButton('Copy Diagnostics')

        wrapper = QWidget(self)
        wrapper.setObjectName('content_area')
        wrapper.setStyleSheet(_CONTENT_QSS)
        inner = QVBoxLayout(wrapper)
        inner.addWidget(self.status_label)
        inner.addWidget(self.message_label)
        inner.addWidget(self.failure_label)
        btn_row = QHBoxLayout()
        for btn in (
            self.install_btn,
            self.repair_btn,
            self.retry_masking_btn,
            self.enable_masking_btn,
            self.disable_masking_btn,
            self.copy_diagnostics_btn,
        ):
            btn_row.addWidget(btn)
        btn_row.addStretch()
        inner.addLayout(btn_row)
        inner.addStretch()

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.addWidget(wrapper)

        self.install_btn.clicked.connect(self._on_install)
        self.repair_btn.clicked.connect(self._on_repair)
        self.retry_masking_btn.clicked.connect(self._on_retry_masking)
        self.enable_masking_btn.clicked.connect(self._on_enable_masking)
        self.disable_masking_btn.clicked.connect(self._on_disable_masking)
        self.copy_diagnostics_btn.clicked.connect(self._on_copy_diagnostics)

        self.refresh()

    @classmethod
    def with_default_service(
        cls, parent: QWidget | None = None
    ) -> DriverStatusPanelWidget:
        """Create the widget with a default VirtualControllerService instance.

        Args:
            parent: Optional Qt parent.

        Returns:
            Widget backed by a freshly created service.

        """
        return cls(
            VirtualControllerService(masking_service=DeviceMaskingService()),
            parent,
        )

    def refresh(self) -> None:
        """Refresh labels and button visibility from the current service state."""
        model = DriverStatusPanelModel.from_service(self._service)
        self.status_label.setText(f'State: {model.runtime_state.value}')
        self.message_label.setText(model.message)
        self.failure_label.setText(
            f'Failure: {model.failure_reason}' if model.failure_reason else ''
        )
        self.install_btn.setVisible('install_driver' in model.actions)
        self.repair_btn.setVisible('repair' in model.actions)
        self.retry_masking_btn.setVisible('retry_masking' in model.actions)
        self.enable_masking_btn.setVisible('enable_masking' in model.actions)
        self.disable_masking_btn.setVisible('disable_masking' in model.actions)
        self.copy_diagnostics_btn.setVisible(
            'copy_diagnostics' in model.actions or model.diagnostics_available
        )

    def _on_install(self) -> None:
        self._service.install_driver()
        self.refresh()

    def _on_repair(self) -> None:
        self._service.repair_driver()
        self.refresh()

    def _on_retry_masking(self) -> None:
        ok = self._service.enable_masking()
        self.refresh()
        if not ok:
            self.failure_label.setText('Masking could not be enabled')

    def _on_enable_masking(self) -> None:
        ok = self._service.enable_masking()
        self.refresh()
        if not ok:
            self.failure_label.setText('Masking could not be enabled')

    def _on_disable_masking(self) -> None:
        ok = self._service.disable_masking()
        self.refresh()
        if not ok:
            self.failure_label.setText('Masking could not be disabled')

    def _on_copy_diagnostics(self) -> None:
        from PySide6.QtWidgets import QApplication

        entries = self._service.copy_diagnostics()
        clipboard = QApplication.clipboard()
        if clipboard is not None and entries:
            clipboard.setText('\n'.join(entries))
        self.refresh()


class AppWindow(QMainWindow):
    """Root application window with industrial dark gaming aesthetic.

    Hosts a branded title bar, always-visible HUD strip, and a panel
    switching area.
    """

    def __init__(
        self,
        shell: ShellModel,
        *,
        role: RoleName | None = None,
        capture_plugin: OpenCVCapturePlugin | None = None,
        virtual_controller_service: VirtualControllerService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize.

        Args:
            shell: Shell model providing route and HUD state.
            role: Role used for route visibility and navigation.
            capture_plugin: Optional capture plugin override for the capture panel.
            virtual_controller_service: Optional service override for the driver
                status panel.  A default instance is created when not provided.
            parent: Optional Qt parent.

        """
        super().__init__(parent)
        self._shell = shell
        self._nav_role = role or RoleName.POWER_GAMER
        self.setWindowTitle(shell.title)
        self.setMinimumSize(960, 600)
        self.resize(1280, 720)
        self.setStyleSheet(_APP_QSS)

        # Dark palette so native decorations match
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(_BG))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(_TEXT))
        palette.setColor(QPalette.ColorRole.Base, QColor(_BG_PANEL))
        palette.setColor(QPalette.ColorRole.Text, QColor(_TEXT))
        self.setPalette(palette)

        hud_model = (
            shell.status_hud
            if shell.status_hud is not None
            else _default_hud_model(shell)
        )
        self.hud_widget = HudWidget(hud_model, parent=self)
        self.route_list = QListWidget(parent=self)
        self.route_list.setObjectName('route_list')
        self.route_list.setStyleSheet(_ROUTE_RAIL_QSS)
        self.panel_host = PanelHost(shell.router, parent=self)
        self.capture_panel = CapturePanelWidget(
            capture_plugin or OpenCVCapturePlugin(),
            parent=self,
        )
        self.driver_status_panel = (
            DriverStatusPanelWidget(virtual_controller_service, parent=self)
            if virtual_controller_service is not None
            else DriverStatusPanelWidget.with_default_service(parent=self)
        )
        self.panel_host.register_panel(EMPTY_PANEL_ID, _build_placeholder_content())
        self._register_route_panels()
        self.panel_host.show_panel(EMPTY_PANEL_ID)
        self._populate_routes()

        # Assemble central widget
        central = QWidget(self)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        title_bar = _build_title_bar(shell.title)
        root_layout.addWidget(title_bar)
        root_layout.addWidget(self.hud_widget)

        body_layout = QHBoxLayout()
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)
        body_layout.addWidget(self.route_list)
        body_layout.addWidget(self.panel_host, stretch=1)
        root_layout.addLayout(body_layout, stretch=1)

        self.setCentralWidget(central)
        self.route_list.currentRowChanged.connect(self._on_route_row_changed)
        self._sync_route_from_shell()

    def navigate_to(self, route_name: str) -> None:
        """Activate a route by name and refresh the visible panel."""
        self.route_list.blockSignals(True)
        try:
            for row in range(self.route_list.count()):
                item = self.route_list.item(row)
                if item.data(Qt.ItemDataRole.UserRole) == route_name:
                    self.route_list.setCurrentRow(row)
                    break
        finally:
            self.route_list.blockSignals(False)
        try:
            panel_id = self._shell.set_active_route(route_name, role=self._nav_role)
        except PermissionError as exc:
            self.statusBar().showMessage(str(exc), 5000)
            return
        self.panel_host.show_panel(panel_id)

    def _populate_routes(self) -> None:
        """Populate the route rail from the router model."""
        self.route_list.clear()
        for route in self._shell.router.available_routes(role=self._nav_role):
            item = QListWidgetItem(route.title)
            item.setData(Qt.ItemDataRole.UserRole, route.name)
            self.route_list.addItem(item)

    def _register_route_panels(self) -> None:
        """Register widgets for known shell panels."""
        self.panel_host.register_panel(
            'panel.home',
            _build_route_placeholder(
                title='Home',
                body='System overview and quick actions will appear here.',
            ),
        )
        self.panel_host.register_panel(
            'panel.catalog',
            _build_route_placeholder(
                title='Catalog',
                body='Plugin catalog rendering is still hosted in the legacy shell.',
            ),
        )
        self.panel_host.register_panel('panel.capture', self.capture_panel)
        self.panel_host.register_panel('panel.output', self.driver_status_panel)
        self.panel_host.register_panel(
            'panel.workers',
            _build_route_placeholder(
                title='Workers',
                body='Worker health and restart controls will appear here.',
            ),
        )
        self.panel_host.register_panel(
            'panel.environment',
            _build_route_placeholder(
                title='Environment',
                body='Environment management tools will appear here.',
            ),
        )
        self.panel_host.register_panel(
            'panel.resources',
            _build_route_placeholder(
                title='Resources',
                body='Online resource browsing will appear here.',
            ),
        )
        self.panel_host.register_panel(
            'panel.admin',
            _build_route_placeholder(
                title='Admin',
                body='Administrative diagnostics and policy tools will appear here.',
            ),
        )

    def _sync_route_from_shell(self) -> None:
        """Sync the visible route rail and panel host from the shell state."""
        active = self._shell.router.active_route
        panel_id = self._shell.active_panel_id()
        if active is None or panel_id is None:
            return
        self.route_list.blockSignals(True)
        try:
            for row in range(self.route_list.count()):
                item = self.route_list.item(row)
                if item.data(Qt.ItemDataRole.UserRole) == active:
                    self.route_list.setCurrentRow(row)
                    break
        finally:
            self.route_list.blockSignals(False)
        self.panel_host.show_panel(panel_id)

    def _on_route_row_changed(self, row: int) -> None:
        """Handle route selection changes from the route rail."""
        if row < 0:
            return
        item = self.route_list.item(row)
        route_name = item.data(Qt.ItemDataRole.UserRole)
        try:
            panel_id = self._shell.set_active_route(route_name, role=self._nav_role)
        except PermissionError as exc:
            self.statusBar().showMessage(str(exc), 5000)
            return
        self.panel_host.show_panel(panel_id)
