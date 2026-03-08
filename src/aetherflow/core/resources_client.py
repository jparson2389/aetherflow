"""Resource manifest validation helpers."""

from __future__ import annotations

from aetherflow.core.resources_manifest import ResourceManifest


class ResourcesClient:
    """Validate signed Online Resources manifests."""

    def validate_manifest(self, manifest: ResourceManifest) -> bool:
        """Return whether a resource manifest is trusted."""
        return manifest.signature == "valid"
