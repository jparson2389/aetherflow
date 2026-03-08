"""Online Resources panel model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResourcesPanelModel:
    """Catalog panel for installable resources."""

    resource_ids: list[str]
    locked_count: int
