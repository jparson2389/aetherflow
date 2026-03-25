"""Panel switching container widget."""

from __future__ import annotations

from PySide6.QtWidgets import QStackedWidget, QVBoxLayout, QWidget

from aetherflow.ui.router import RouterModel


class PanelHost(QWidget):
    """Container that hosts and switches between registered panel widgets."""

    def __init__(self, router: RouterModel, parent: QWidget | None = None) -> None:
        """Initialize."""
        super().__init__(parent)
        self._router = router
        self._panels: dict[str, QWidget] = {}
        self._stack = QStackedWidget(self)
        self._active: str | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._stack)

    def register_panel(self, panel_id: str, widget: QWidget) -> None:
        """Register a widget under a panel identifier.

        Args:
            panel_id: Unique panel identifier matching a RouteDefinition.
            widget: The Qt widget to display for that panel.

        """
        self._panels[panel_id] = widget
        self._stack.addWidget(widget)

    def show_panel(self, panel_id: str) -> None:
        """Switch the visible panel.

        Args:
            panel_id: The panel to make active.

        Raises:
            KeyError: If the panel_id has not been registered.

        """
        if panel_id not in self._panels:
            raise KeyError(f'Panel not registered: {panel_id}')
        self._stack.setCurrentWidget(self._panels[panel_id])
        self._active = panel_id

    def current_panel_id(self) -> str | None:
        """Return the currently active panel identifier.

        Returns:
            Active panel id, or None if no panel has been shown yet.

        """
        return self._active
