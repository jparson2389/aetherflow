"""PySide6 implementation of the plugin catalog view."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from aetherflow.ui.panels.plugin_catalog_panel import (
        CatalogEntry,
        PluginCatalogPanelModel,
    )


class PluginItemWidget(QWidget):
    """Widget representing a single plugin in the catalog."""

    def __init__(self, entry: CatalogEntry, parent: QWidget | None = None) -> None:
        """Initialize the plugin item with its metadata."""
        super().__init__(parent)
        self.setFixedHeight(80)
        self.setStyleSheet(
            'QWidget { background-color: #1e1e30; border-radius: 6px; border: 1px solid #2e2e42; }'
            'QWidget:hover { border: 1px solid #000000; }'
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)

        # Icon/Type Label
        type_label = QLabel(entry.plugin_type.value[:1].upper())
        type_label.setFixedSize(40, 40)
        type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        type_label.setStyleSheet(
            'background-color: #2c2c44; border-radius: 20px; font-weight: bold; color: #9b59b6;'
        )
        layout.addWidget(type_label)

        # Info Labels
        info_layout = QVBoxLayout()
        name_label = QLabel(entry.name)
        name_label.setStyleSheet('font-weight: bold; font-size: 14px; border: none;')
        ver_label = QLabel(f'v{entry.version} (API {entry.api_version})')
        ver_label.setStyleSheet('color: #a0a0b0; border: none; font-size: 11px;')
        info_layout.addWidget(name_label)
        info_layout.addWidget(ver_label)
        layout.addLayout(info_layout)

        layout.addStretch()

        # Status Label
        status_label = QLabel(entry.lock_state.value)
        status_label.setFixedWidth(80)
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        status_colors = {
            'AVAILABLE': '#2ecc71',
            'GRACE': '#f1c40f',
            'LOCKED': '#e74c3c'
        }
        color = status_colors.get(entry.lock_state.value, '#e1e1e1')
        status_label.setStyleSheet(
            f'color: {color}; font-weight: bold; border: 1px solid {color}; border-radius: 4px; padding: 2px;'
        )
        layout.addWidget(status_label)


class PluginCatalogView(QWidget):
    """View for browsing the plugin catalog."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the catalog view container."""
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header = QLabel('Plugin Catalog')
        header.setStyleSheet('font-size: 24px; font-weight: bold; margin-bottom: 10px;')
        self.layout.addWidget(header)

        # Summary Stats
        self.stats_label = QLabel('0 Available | 0 In Grace | 0 Locked')
        self.stats_label.setStyleSheet('color: #a0a0b0; margin-bottom: 20px;')
        self.layout.addWidget(self.stats_label)

        # Scrollable Area for Plugins
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet('QScrollArea { border: none; background-color: transparent; }')
        
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.container_layout.setSpacing(10)
        
        self.scroll.setWidget(self.container)
        self.layout.addWidget(self.scroll)

    def update_from_model(self, model: PluginCatalogPanelModel) -> None:
        """Refresh the plugin list from the catalog model."""
        # Clear existing items
        for i in reversed(range(self.container_layout.count())):
            item = self.container_layout.itemAt(i)
            if item and item.widget():
                item.widget().setParent(None)

        # Update Stats
        self.stats_label.setText(
            f'{model.available_count} Available | '
            f'{model.grace_count} In Grace | '
            f'{model.locked_count} Locked'
        )

        # Add Plugin Items
        for entry in model.entries:
            self.container_layout.addWidget(PluginItemWidget(entry))
