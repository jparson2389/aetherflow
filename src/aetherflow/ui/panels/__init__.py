"""Panel models for the Aetherflow shell."""

from aetherflow.ui.panels.admin_panel import AdminPanelModel
from aetherflow.ui.panels.capture_diagnostics_panel import CaptureDiagnosticsPanelModel
from aetherflow.ui.panels.environment_panel import (
    EnvironmentPanelModel,
    EnvironmentSummary,
)
from aetherflow.ui.panels.plugin_catalog_panel import PluginCatalogPanelModel
from aetherflow.ui.panels.resources_panel import ResourceItemModel, ResourcesPanelModel
from aetherflow.ui.panels.worker_health_panel import WorkerHealthPanelModel

__all__ = [
    'AdminPanelModel',
    'CaptureDiagnosticsPanelModel',
    'EnvironmentPanelModel',
    'EnvironmentSummary',
    'PluginCatalogPanelModel',
    'ResourceItemModel',
    'ResourcesPanelModel',
    'WorkerHealthPanelModel',
]
