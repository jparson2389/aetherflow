"""Plugin catalog panel model."""

from __future__ import annotations

from dataclasses import dataclass, field

from aetherflow.core.entitlements import RoleName
from aetherflow.plugins.catalog import CatalogEntry, CatalogLockState
from aetherflow.plugins.registry import PluginRegistry


@dataclass(slots=True)
class PluginCatalogPanelModel:
    """Simple catalog panel model."""

    entries: list[CatalogEntry] = field(default_factory=list)
    locked_count: int = 0
    grace_count: int = 0
    available_count: int = 0

    @classmethod
    def from_registry(
        cls,
        registry: PluginRegistry,
        *,
        role: RoleName,
    ) -> PluginCatalogPanelModel:
        """Build a catalog panel from the plugin registry.

        Args:
            registry: Plugin registry providing catalog entries.
            role: Role to filter visible entries.

        Returns:
            Plugin catalog panel model.

        """
        entries = registry.catalog_for_role(role)
        locked_count = sum(
            1 for entry in entries if entry.lock_state is CatalogLockState.LOCKED
        )
        grace_count = sum(
            1 for entry in entries if entry.lock_state is CatalogLockState.GRACE
        )
        available_count = sum(
            1 for entry in entries if entry.lock_state is CatalogLockState.AVAILABLE
        )
        return cls(
            entries=entries,
            locked_count=locked_count,
            grace_count=grace_count,
            available_count=available_count,
        )
