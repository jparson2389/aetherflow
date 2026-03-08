"""Plugin catalog panel model."""

from __future__ import annotations

from dataclasses import dataclass, field

from aetherflow.plugins.catalog import CatalogEntry


@dataclass(slots=True)
class PluginCatalogPanelModel:
    """Simple catalog panel model."""

    entries: list[CatalogEntry] = field(default_factory=list)
