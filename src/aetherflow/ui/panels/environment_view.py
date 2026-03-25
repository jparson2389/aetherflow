"""PySide6 implementation of the environment management view."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from aetherflow.ui.panels.environment_panel import (
        EnvironmentPanelModel,
        EnvironmentSummary,
    )


class EnvironmentItemWidget(QWidget):
    """Widget representing a single Python environment."""

    def __init__(self, summary: EnvironmentSummary, parent: QWidget | None = None) -> None:
        """Initialize the environment item with its metadata."""
        super().__init__(parent)
        self.setFixedHeight(100)
        self.setStyleSheet(
            'QWidget { background-color: #1e1e30; border-radius: 6px; border: 1px solid #2e2e42; }'
            'QWidget:hover { border: 1px solid #000000; }'
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)

        # Info Labels
        info_layout = QVBoxLayout()
        name_label = QLabel(summary.name)
        name_label.setStyleSheet('font-weight: bold; font-size: 14px; border: none;')
        ver_label = QLabel(f'Python {summary.python_version}')
        ver_label.setStyleSheet('color: #a0a0b0; border: none; font-size: 11px;')
        dep_label = QLabel(f'{summary.dependency_count} dependencies')
        dep_label.setStyleSheet('color: #a0a0b0; border: none; font-size: 11px;')
        
        info_layout.addWidget(name_label)
        info_layout.addWidget(ver_label)
        info_layout.addWidget(dep_label)
        layout.addLayout(info_layout)

        layout.addStretch()

        # Status and Actions
        status_layout = QVBoxLayout()
        status_label = QLabel(summary.validation_status.upper())
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        status_colors = {
            'VALID': '#2ecc71',
            'FAILED': '#e74c3c',
            'PENDING': '#f1c40f'
        }
        color = status_colors.get(summary.validation_status.upper(), '#e1e1e1')
        status_label.setStyleSheet(f'color: {color}; font-weight: bold; font-size: 10px;')
        status_layout.addWidget(status_label)

        repair_btn = QPushButton('Repair')
        repair_btn.setFixedSize(60, 24)
        repair_btn.setStyleSheet(
            'QPushButton { background-color: #2c2c44; border: 1px solid #3e3e5a; border-radius: 3px; font-size: 10px; }'
            'QPushButton:hover { background-color: #3e3e5a; }'
        )
        status_layout.addWidget(repair_btn)
        layout.addLayout(status_layout)


class EnvironmentView(QWidget):
    """View for managing Python environments."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the environment view container."""
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header = QLabel('Environment Manager')
        header.setStyleSheet('font-size: 24px; font-weight: bold; margin-bottom: 10px;')
        self.layout.addWidget(header)

        # Summary Stats
        self.stats_label = QLabel('0 Environments | 0 Failed | 0 Pending')
        self.stats_label.setStyleSheet('color: #a0a0b0; margin-bottom: 20px;')
        self.layout.addWidget(self.stats_label)

        # Scroll Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet('QScrollArea { border: none; background-color: transparent; }')
        
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.container_layout.setSpacing(10)
        
        self.scroll.setWidget(self.container)
        self.layout.addWidget(self.scroll)

    def update_from_model(self, model: EnvironmentPanelModel) -> None:
        """Refresh the environment list from the model."""
        # Clear existing items
        for i in reversed(range(self.container_layout.count())):
            item = self.container_layout.itemAt(i)
            if item and item.widget():
                item.widget().setParent(None)

        # Update Stats
        total = len(model.environments)
        self.stats_label.setText(
            f'{total} Environments | '
            f'{model.failed_count} Failed | '
            f'{model.pending_count} Pending'
        )

        # Add Items
        for summary in model.environments:
            self.container_layout.addWidget(EnvironmentItemWidget(summary))
