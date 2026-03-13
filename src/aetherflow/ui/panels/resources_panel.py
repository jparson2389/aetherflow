"""Online Resources panel model."""

from __future__ import annotations

from dataclasses import dataclass, field

from aetherflow.core.resources_manifest import ResourceEntry, ResourceManifest


@dataclass(frozen=True, slots=True)
class ResourceItemModel:
    """Resource entry for the UI catalog."""

    resource_id: str
    kind: str
    version: str
    size: int
    premium: bool
    required_tier: str | None
    lock_state: str
    actions: list[str]

    @classmethod
    def from_entry(
        cls,
        entry: ResourceEntry,
        *,
        unlocked: bool,
    ) -> ResourceItemModel:
        """Build a resource item model from a manifest entry.

        Args:
            entry: Resource manifest entry.
            unlocked: Whether the resource is unlocked for install.

        Returns:
            Resource item model.

        """
        lock_state = 'available' if unlocked or not entry.premium else 'locked'
        actions = ['install']
        if entry.premium and not unlocked:
            actions.append('upgrade')
        return cls(
            resource_id=entry.resource_id,
            kind=entry.kind,
            version=entry.version,
            size=entry.size,
            premium=entry.premium,
            required_tier=entry.required_tier,
            lock_state=lock_state,
            actions=actions,
        )


@dataclass(frozen=True, slots=True)
class ResourcesPanelModel:
    """Catalog panel for installable resources."""

    resources: list[ResourceItemModel] = field(default_factory=list)
    locked_count: int = 0

    @classmethod
    def from_manifest(
        cls,
        manifest: ResourceManifest,
        *,
        unlocked_resource_ids: set[str] | None = None,
    ) -> ResourcesPanelModel:
        """Build a resources panel from a manifest.

        Args:
            manifest: Resource manifest to render.
            unlocked_resource_ids: Resource ids granted by entitlements.

        Returns:
            Resources panel model.

        """
        unlocked_resource_ids = unlocked_resource_ids or set()
        items = [
            ResourceItemModel.from_entry(
                entry,
                unlocked=entry.resource_id in unlocked_resource_ids,
            )
            for entry in manifest.resources
        ]
        locked_count = sum(1 for item in items if item.lock_state == 'locked')
        return cls(resources=items, locked_count=locked_count)
