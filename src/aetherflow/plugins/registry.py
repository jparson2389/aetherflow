"""Plugin registry and catalog orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from aetherflow.core.entitlements import EntitlementState, RoleName
from aetherflow.core.services import AppServices
from aetherflow.plugins.catalog import CatalogEntry, CatalogLockState
from aetherflow.plugins.manifest import PluginManifest


@dataclass(frozen=True, slots=True)
class RegistrationResult:
    """Result of a plugin registration attempt."""

    loaded: bool
    reason: str | None = None
    state: EntitlementState | None = None


class PluginRegistry:
    """Trust-aware plugin registry."""

    def __init__(self, *, services: AppServices) -> None:
        """Create a plugin registry.

        Args:
            services: Shared application services for trust and entitlement checks.
        """
        self._services = services
        self._plugins: dict[str, PluginManifest] = {}
        self._catalog: list[CatalogEntry] = []

    def register(self, manifest: PluginManifest) -> RegistrationResult:
        """Validate and register a plugin manifest."""
        if not self._services.trust_verifier.verify(manifest):
            entry = self._catalog_entry(
                manifest,
                lock_state=CatalogLockState.LOCKED,
                selectable=False,
                purchase_cta="Signed publisher certificate required",
            )
            self._catalog.append(entry)
            return RegistrationResult(loaded=False, reason="unsigned-plugin")

        entitlement_state = self._services.entitlements.evaluate(
            manifest.plugin_id,
            tuple(manifest.required_entitlements),
        )
        if manifest.premium and entitlement_state is EntitlementState.LOCKED:
            self._catalog.append(
                self._catalog_entry(
                    manifest,
                    lock_state=CatalogLockState.LOCKED,
                    selectable=False,
                    purchase_cta="Upgrade to unlock",
                )
            )
            return RegistrationResult(
                loaded=False,
                reason="locked-premium-plugin",
                state=entitlement_state,
            )

        lock_state = (
            CatalogLockState.GRACE
            if entitlement_state is EntitlementState.GRACE
            else CatalogLockState.AVAILABLE
        )
        self._plugins[manifest.plugin_id] = manifest
        self._catalog.append(
            self._catalog_entry(
                manifest,
                lock_state=lock_state,
                selectable=True,
                purchase_cta=None,
            )
        )
        return RegistrationResult(loaded=True, state=entitlement_state)

    def get(self, plugin_id: str) -> PluginManifest | None:
        """Return a registered plugin manifest."""
        return self._plugins.get(plugin_id)

    def catalog(self) -> list[CatalogEntry]:
        """Return all catalog entries."""
        return list(self._catalog)

    def catalog_for_role(self, role: RoleName) -> list[CatalogEntry]:
        """Return catalog entries visible to a role."""
        return [entry for entry in self._catalog if role in entry.allowed_roles]

    def _catalog_entry(
        self,
        manifest: PluginManifest,
        *,
        lock_state: CatalogLockState,
        selectable: bool,
        purchase_cta: str | None,
    ) -> CatalogEntry:
        allowed_roles = (
            RoleName.POWER_GAMER,
            RoleName.VISION_ML_TINKERER,
            RoleName.ACCESSIBILITY_MODDER,
            RoleName.ADMIN_OPERATOR,
        )
        return CatalogEntry(
            plugin_id=manifest.plugin_id,
            display_name=manifest.name,
            lock_state=lock_state,
            selectable=selectable,
            purchase_cta=purchase_cta,
            allowed_roles=allowed_roles,
        )
