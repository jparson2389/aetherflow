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
    required_tier: str | None

    @classmethod
    def from_entry(cls, entry: ResourceEntry) -> ResourceDetailsModalModel:
        """Build a modal model from a resource entry."""
        lock_state = "locked" if entry.premium else "available"
        actions = ["install"]
        if entry.premium:
            actions.append("upgrade")
        return cls(
            resource_id=entry.resource_id,
            lock_state=lock_state,
            actions=actions,
            required_tier=entry.required_tier,
        )
