"""Catalog models for plugin selection UX."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from aetherflow.core.entitlements import EntitlementState, RoleName
from aetherflow.plugins.manifest import PluginManifest, PluginType


class CatalogLockState(StrEnum):
    """Catalog lock states."""

    AVAILABLE = 'AVAILABLE'
    LOCKED = 'LOCKED'
    GRACE = 'GRACE'


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    """UI catalog entry for a plugin."""

    plugin_id: str
    display_name: str
    lock_state: CatalogLockState
    selectable: bool
    purchase_cta: str | None
    allowed_roles: tuple[RoleName, ...]
    plugin_type: PluginType | None = None
    version: str | None = None
    premium: bool = False
    required_entitlements: tuple[str, ...] = ()
    requires_worker: bool = False
    requires_drivers: tuple[str, ...] = ()
    entitlement_state: EntitlementState | None = None
    lock_reason: str | None = None


def build_catalog_entry(
    manifest: PluginManifest,
    *,
    lock_state: CatalogLockState,
    selectable: bool,
    purchase_cta: str | None,
    allowed_roles: tuple[RoleName, ...],
    entitlement_state: EntitlementState | None,
    lock_reason: str | None = None,
) -> CatalogEntry:
    """Build a catalog entry from a plugin manifest.

    Args:
        manifest: Plugin manifest containing metadata.
        lock_state: Catalog lock state.
        selectable: Whether the plugin may be selected.
        purchase_cta: Optional purchase call-to-action.
        allowed_roles: Roles that can see the plugin.
        entitlement_state: Entitlement state for the plugin.
        lock_reason: Optional lock reason code.

    Returns:
        Catalog entry populated with manifest metadata.

    """
    return CatalogEntry(
        plugin_id=manifest.plugin_id,
        display_name=manifest.name,
        lock_state=lock_state,
        selectable=selectable,
        purchase_cta=purchase_cta,
        allowed_roles=allowed_roles,
        plugin_type=manifest.plugin_type,
        version=str(manifest.version),
        premium=manifest.premium,
        required_entitlements=tuple(manifest.required_entitlements),
        requires_worker=manifest.requires_worker,
        requires_drivers=tuple(manifest.requires_drivers),
        entitlement_state=entitlement_state,
        lock_reason=lock_reason,
    )


def lock_state_for_entitlement(state: EntitlementState) -> CatalogLockState:
    """Map entitlement state to catalog lock state.

    Args:
        state: Entitlement state to map.

    Returns:
        Catalog lock state.

    """
    if state is EntitlementState.GRACE:
        return CatalogLockState.GRACE
    if state is EntitlementState.LOCKED:
        return CatalogLockState.LOCKED
    return CatalogLockState.AVAILABLE
