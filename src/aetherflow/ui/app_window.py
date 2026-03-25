"""Main application window — industrial dark / gaming HUD aesthetic."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from aetherflow.core.entitlements import EntitlementState
from aetherflow.ui.hud_widget import HudWidget
from aetherflow.ui.panel_host import PanelHost
from aetherflow.ui.shell import ShellModel
from aetherflow.ui.status_hud import StatusHUDModel

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


class AppWindow(QMainWindow):
    """Root application window with industrial dark gaming aesthetic.

    Hosts a branded title bar, always-visible HUD strip, and a panel
    switching area.
    """

    def __init__(self, shell: ShellModel, parent: QWidget | None = None) -> None:
        """Initialize."""
        super().__init__(parent)
        self._shell = shell
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
        self.panel_host = PanelHost(shell.router, parent=self)
        self.panel_host.register_panel(EMPTY_PANEL_ID, _build_placeholder_content())
        self.panel_host.show_panel(EMPTY_PANEL_ID)

        # Assemble central widget
        central = QWidget(self)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        title_bar = _build_title_bar(shell.title)
        root_layout.addWidget(title_bar)
        root_layout.addWidget(self.hud_widget)
        root_layout.addWidget(self.panel_host, stretch=1)

        self.setCentralWidget(central)
