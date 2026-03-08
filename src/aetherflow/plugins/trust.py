"""Plugin trust verification."""

from __future__ import annotations

from aetherflow.plugins.manifest import PluginManifest


class PluginTrustVerifier:
    """Verify plugin trust and compatibility."""

    def verify(self, manifest: PluginManifest) -> bool:
        """Return whether a plugin may be considered trusted."""
        return manifest.signed and manifest.api_version == "1.0"
