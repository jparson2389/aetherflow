"""Premium Media Foundation capture model."""

from __future__ import annotations

from dataclasses import dataclass

from aetherflow.core.entitlements import EntitlementState
from aetherflow.core.services import AppServices
from aetherflow.plugins.catalog import (
    CatalogEntry,
    build_catalog_entry,
    lock_state_for_entitlement,
)
from aetherflow.plugins.manifest import PluginManifest, PluginType, PluginVersion


@dataclass(frozen=True, slots=True)
class CaptureFormatSelector:
    """Format selector for premium capture backends."""

    formats: list[str]
    unavailable_reason: str | None = None


class MediaFoundationCapturePlugin:
    """Premium Media Foundation capture backend."""

    def __init__(self, *, services: AppServices) -> None:
        """Create the premium capture plugin model.

        Args:
            services: Shared application services for entitlement checks.

        """
        self._services = services
        self._manifest = PluginManifest(
            plugin_id='capture.mf',
            name='MF Capture',
            version=PluginVersion.parse('1.0.0'),
            api_version='1.0',
            plugin_type=PluginType.CAPTURE,
            entrypoint='capture.mf.dll',
            signed=True,
            premium=True,
            required_entitlements=['vision'],
            requires_worker=False,
            signature_scheme='Authenticode',
            digest_algorithm='SHA-256',
            rsa_key_bits=3072,
            publisher_thumbprint='aetherflow-publisher',
            trust_root_thumbprint='aetherflow-root',
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
        entitlement_state = self._services.entitlements.evaluate(
            self._manifest.plugin_id,
            tuple(self._manifest.required_entitlements),
        )
        lock_state = lock_state_for_entitlement(entitlement_state)
        selectable = entitlement_state is not EntitlementState.LOCKED
        return build_catalog_entry(
            self._manifest,
            lock_state=lock_state,
            selectable=selectable,
            purchase_cta=None if selectable else 'Upgrade to unlock',
            allowed_roles=tuple(role.name for role in self._services.roles),
            entitlement_state=entitlement_state,
            lock_reason='locked-premium-plugin' if not selectable else None,
        )

    def format_selector(self) -> CaptureFormatSelector:
        """Return available format options based on entitlement state."""
        if not self.is_available():
            return CaptureFormatSelector(
                formats=[],
                unavailable_reason='Upgrade to unlock',
            )
        return CaptureFormatSelector(formats=['NV12', 'YUY2', 'MJPEG'])
