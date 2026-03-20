"""Plugin registry and catalog orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from aetherflow.core.entitlements import EntitlementState, RoleName
from aetherflow.core.services import AppServices
from aetherflow.plugins.catalog import (
    CatalogEntry,
    CatalogLockState,
    build_catalog_entry,
    lock_state_for_entitlement,
)
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
        self._catalog_ids: set[str] = set()

    def register(self, manifest: PluginManifest) -> RegistrationResult:
        """Validate and register a plugin manifest."""
        if manifest.plugin_id in self._catalog_ids:
            return RegistrationResult(loaded=False, reason='duplicate-plugin-id')
        trust_result = self._services.trust_verifier.verify(manifest)
        if not trust_result.trusted:
            reason = trust_result.reason or 'untrusted-plugin'
            entry = self._catalog_entry(
                manifest,
                lock_state=CatalogLockState.LOCKED,
                selectable=False,
                purchase_cta='Signed publisher certificate required',
                entitlement_state=EntitlementState.LOCKED,
                lock_reason=reason,
            )
            self._catalog.append(entry)
            self._catalog_ids.add(manifest.plugin_id)
            return RegistrationResult(loaded=False, reason=reason)

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
                    purchase_cta='Upgrade to unlock',
                    entitlement_state=entitlement_state,
                    lock_reason='locked-premium-plugin',
                )
            )
            self._catalog_ids.add(manifest.plugin_id)
            return RegistrationResult(
                loaded=False,
                reason='locked-premium-plugin',
                state=entitlement_state,
            )

        lock_state = lock_state_for_entitlement(entitlement_state)
        self._plugins[manifest.plugin_id] = manifest
        self._catalog.append(
            self._catalog_entry(
                manifest,
                lock_state=lock_state,
                selectable=True,
                purchase_cta=None,
                entitlement_state=entitlement_state,
                lock_reason=None,
            )
        )
        self._catalog_ids.add(manifest.plugin_id)
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
        entitlement_state: EntitlementState | None,
        lock_reason: str | None,
    ) -> CatalogEntry:
        allowed_roles = tuple(RoleName)
        return build_catalog_entry(
            manifest,
            lock_state=lock_state,
            selectable=selectable,
            purchase_cta=purchase_cta,
            allowed_roles=allowed_roles,
            entitlement_state=entitlement_state,
            lock_reason=lock_reason,
        )
