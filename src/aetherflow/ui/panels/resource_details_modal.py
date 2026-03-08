"""Resource details modal model."""

from __future__ import annotations

from dataclasses import dataclass

from aetherflow.core.resources_manifest import ResourceEntry


@dataclass(frozen=True, slots=True)
class ResourceDetailsModalModel:
    """Details modal state for an installable resource."""

    resource_id: str
    lock_state: str
    actions: list[str]

    @classmethod
    def from_entry(cls, entry: ResourceEntry) -> ResourceDetailsModalModel:
        """Build a modal model from a resource entry."""
        lock_state = "locked" if entry.premium else "available"
        return cls(
            resource_id=entry.resource_id, lock_state=lock_state, actions=["install"]
        )
