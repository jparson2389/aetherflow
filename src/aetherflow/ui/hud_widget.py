"""Status HUD Qt widget — always-visible telemetry strip."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QWidget

from aetherflow.ui.status_hud import StatusHUDModel

# ── Palette ──────────────────────────────────────────────────────────────────
_BG = '#0f1114'
_BORDER = '#1e2229'
_AMBER = '#f5a623'
_AMBER_DIM = '#7a5012'
_GREEN = '#4caf6e'
_RED = '#e05252'
_YELLOW = '#d4a017'
_MUTED = '#4a5568'
_TEXT = '#c8d0dc'

_STATE_COLORS: dict[str, str] = {
    'RUNNING': _GREEN,
    'DEGRADED': _YELLOW,
    'RECOVERING': _YELLOW,
    'FAILED': _RED,
    'LOCKED': _RED,
    'GRACE': _AMBER,
}

_HUD_QSS = f"""
HudWidget {{
    background-color: {_BG};
    border-bottom: 1px solid {_BORDER};
}}
QLabel {{
    color: {_TEXT};
    font-family: "Consolas", "Courier New", monospace;
    font-size: 11px;
    letter-spacing: 0.5px;
    background: transparent;
}}
QLabel#fps_label {{
    color: {_AMBER};
    font-size: 12px;
    font-weight: bold;
    letter-spacing: 1px;
}}
QLabel#jitter_label {{
    color: {_MUTED};
    font-size: 10px;
}}
QLabel#plugin_label {{
    color: {_MUTED};
    font-size: 10px;
    letter-spacing: 0.3px;
}}
QFrame#separator {{
    background-color: {_BORDER};
    max-width: 1px;
    min-width: 1px;
}}
"""


class _StatePill(QWidget):
    """Color-coded runtime state badge."""

    def __init__(self, state: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._state = state
        self._color = QColor(_STATE_COLORS.get(state, _MUTED))
        self.setFixedSize(QSize(80, 18))

    def update_state(self, state: str) -> None:
        self._state = state
        self._color = QColor(_STATE_COLORS.get(state, _MUTED))
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(1, 2, -1, -2)
        path = QPainterPath()
        path.addRoundedRect(rect.x(), rect.y(), rect.width(), rect.height(), 2, 2)
        fill = QColor(self._color)
        fill.setAlpha(30)
        p.fillPath(path, fill)
        pen_color = QColor(self._color)
        p.setPen(pen_color)
        p.drawPath(path)
        p.setPen(QColor(self._color))
        font = p.font()
        font.setFamily('Consolas')
        font.setPointSize(8)
        font.setLetterSpacing(font.SpacingType.AbsoluteSpacing, 1.2)
        font.setBold(True)
        p.setFont(font)
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, self._state)
        p.end()


def _vline() -> QFrame:
    line = QFrame()
    line.setObjectName('separator')
    line.setFrameShape(QFrame.Shape.VLine)
    line.setFixedWidth(1)
    line.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
    return line


def _label(text: str, name: str | None = None) -> QLabel:
    lbl = QLabel(text)
    if name:
        lbl.setObjectName(name)
    return lbl


class HudWidget(QWidget):
    """Always-visible telemetry strip rendered as an industrial HUD bar."""

    def __init__(self, model: StatusHUDModel, parent: QWidget | None = None) -> None:
        """Initialize."""
        super().__init__(parent)
        self._model = model
        self.setFixedHeight(28)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(_HUD_QSS)

        self._pill = _StatePill(model.runtime_state.value, parent=self)
        self._fps_label = _label('', 'fps_label')
        self._jitter_label = _label('', 'jitter_label')
        self._input_label = _label('', 'plugin_label')
        self._output_label = _label('', 'plugin_label')
        self._ent_label = _label('', 'plugin_label')

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(10)

        layout.addWidget(self._pill)
        layout.addWidget(_vline())
        layout.addWidget(self._fps_label)
        layout.addWidget(self._jitter_label)
        layout.addWidget(_vline())
        layout.addWidget(_label('IN:', 'plugin_label'))
        layout.addWidget(self._input_label)
        layout.addWidget(_label('OUT:', 'plugin_label'))
        layout.addWidget(self._output_label)
        layout.addStretch()
        layout.addWidget(self._ent_label)

        self._refresh()

    def _refresh(self) -> None:
        m = self._model
        self._pill.update_state(m.runtime_state.value)
        self._fps_label.setText(f'{m.measured_fps:.0f} FPS')
        self._jitter_label.setText(f'±{m.jitter_ms:.1f}ms')
        self._input_label.setText(m.input_plugin)
        self._output_label.setText(m.output_plugin)
        self._ent_label.setText(f'ENT:{m.entitlement_state.value}')

    def runtime_state_text(self) -> str:
        """Return text representation of the current runtime state."""
        return self._model.runtime_state.value

    def fps_text(self) -> str:
        """Return the FPS label text."""
        return self._fps_label.text()

    def update_model(self, model: StatusHUDModel) -> None:
        """Replace the HUD model and refresh all labels.

        Args:
            model: New status HUD data.

        """
        self._model = model
        self._refresh()
