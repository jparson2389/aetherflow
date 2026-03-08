"""Premium Media Foundation capture model."""

from __future__ import annotations

from aetherflow.core.entitlements import EntitlementState
from aetherflow.core.services import AppServices
from aetherflow.plugins.catalog import CatalogEntry, CatalogLockState
from aetherflow.plugins.manifest import PluginManifest, PluginType, PluginVersion


class MediaFoundationCapturePlugin:
    """Premium Media Foundation capture backend."""

    def __init__(self, *, services: AppServices) -> None:
        """Create the premium capture plugin model.

        Args:
            services: Shared application services for entitlement checks.
        """
        self._services = services
        self._manifest = PluginManifest(
            plugin_id="capture.mf",
            name="MF Capture",
            version=PluginVersion.parse("1.0.0"),
            api_version="1.0",
            plugin_type=PluginType.CAPTURE,
            entrypoint="capture.mf.dll",
            signed=True,
            premium=True,
            required_entitlements=["vision"],
            requires_worker=False,
        )

    def is_available(self) -> bool:
        """Return whether the backend is selectable."""
        return (
            self._services.entitlements.evaluate(
                self._manifest.plugin_id,
                tuple(self._manifest.required_entitlements),
            )
            is not EntitlementState.LOCKED
        )

    def catalog_state(self) -> CatalogEntry:
        """Return the catalog state for the plugin."""
        return CatalogEntry(
            plugin_id=self._manifest.plugin_id,
            display_name=self._manifest.name,
            lock_state=(
                CatalogLockState.AVAILABLE
                if self.is_available()
                else CatalogLockState.LOCKED
            ),
            selectable=self.is_available(),
            purchase_cta=None if self.is_available() else "Upgrade to unlock",
            allowed_roles=tuple(role.name for role in self._services.roles),
        )
