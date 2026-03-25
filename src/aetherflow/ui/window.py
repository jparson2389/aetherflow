"""Primary shell window used by UI tests (route list, stacked panels, catalog)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from aetherflow.core.entitlements import RoleName
from aetherflow.ui.panels.plugin_catalog_panel import PluginCatalogPanelModel
from aetherflow.ui.shell import ShellModel


class PluginCatalogPanelWidget(QWidget):
    """Catalog view bound to :class:`PluginCatalogPanelModel`."""

    def __init__(self, model: PluginCatalogPanelModel | None) -> None:
        """Create a catalog widget from the shell catalog model.

        Args:
            model: Catalog data from the shell, or None when unset.

        """
        super().__init__()
        self.summary_label = QLabel()
        self.entry_list = QListWidget()
        layout = QVBoxLayout(self)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.entry_list)
        if model is not None:
            self.summary_label.setText(
                f'{model.available_count} available, {model.locked_count} locked, '
                f'{model.grace_count} grace'
            )
            for entry in model.entries:
                text = f'{entry.display_name} — {entry.lock_state.value}'
                self.entry_list.addItem(QListWidgetItem(text))


class AetherflowMainWindow(QMainWindow):
    """Test-oriented main window with route navigation and panel placeholders."""

    def __init__(
        self,
        shell: ShellModel,
        *,
        role: RoleName | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """Wire a window to the shell model for a given navigation role.

        Args:
            shell: Configured shell.
            role: Role used for route visibility; defaults to POWER_GAMER.
            parent: Optional Qt parent.

        """
        super().__init__(parent)
        self._shell = shell
        self._nav_role = role or RoleName.POWER_GAMER
        self.setWindowTitle(shell.title)

        central = QWidget()
        main_layout = QVBoxLayout(central)

        self.route_list = QListWidget()
        self._populate_routes()
        main_layout.addWidget(self.route_list)

        self.runtime_state_value = QLabel(shell.runtime_state.value)
        main_layout.addWidget(self.runtime_state_value)

        self.panel_title_label = QLabel()
        self.panel_body_label = QLabel()
        self.panel_body_label.setWordWrap(True)

        generic = QWidget()
        generic_layout = QVBoxLayout(generic)
        generic_layout.addWidget(self.panel_title_label)
        generic_layout.addWidget(self.panel_body_label)

        self.catalog_panel = PluginCatalogPanelWidget(shell.plugin_catalog)

        self.panel_stack = QStackedWidget()
        self.panel_stack.addWidget(generic)
        self.panel_stack.addWidget(self.catalog_panel)

        main_layout.addWidget(self.panel_stack)

        self.notices_list = QListWidget()
        self._refresh_notices()
        main_layout.addWidget(self.notices_list)

        self.setCentralWidget(central)
        self.route_list.currentRowChanged.connect(self._on_route_row_changed)
        self._sync_route_from_shell()

    def _populate_routes(self) -> None:
        self.route_list.clear()
        for route in self._shell.router.available_routes(role=self._nav_role):
            item = QListWidgetItem(route.title)
            item.setData(Qt.ItemDataRole.UserRole, route.name)
            self.route_list.addItem(item)

    def _refresh_notices(self) -> None:
        self.notices_list.clear()
        for notice in self._shell.notices:
            self.notices_list.addItem(QListWidgetItem(notice.message))

    def _sync_route_from_shell(self) -> None:
        active = self._shell.router.active_route
        if active is None:
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
        self._apply_route(active)

    def _on_route_row_changed(self, row: int) -> None:
        if row < 0:
            return
        item = self.route_list.item(row)
        name = item.data(Qt.ItemDataRole.UserRole)
        self._shell.set_active_route(name, role=self._nav_role)
        self._apply_route(name)

    def navigate_to(self, route_name: str) -> None:
        """Activate a route by name and refresh the panel area."""
        self.route_list.blockSignals(True)
        try:
            for row in range(self.route_list.count()):
                item = self.route_list.item(row)
                if item.data(Qt.ItemDataRole.UserRole) == route_name:
                    self.route_list.setCurrentRow(row)
                    break
        finally:
            self.route_list.blockSignals(False)
        self._shell.set_active_route(route_name, role=self._nav_role)
        self._apply_route(route_name)

    def _apply_route(self, route_name: str) -> None:
        route = self._shell.router.routes.get(route_name)
        if route is None:
            return
        if route_name == 'catalog':
            self.panel_stack.setCurrentWidget(self.catalog_panel)
            self.panel_title_label.setText(route.title)
            self.panel_body_label.setText('catalog')
        else:
            self.panel_stack.setCurrentIndex(0)
            self.panel_title_label.setText(route.title)
            self.panel_body_label.setText(f'{route.name} panel content placeholder.')
