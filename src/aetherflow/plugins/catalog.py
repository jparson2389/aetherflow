"""Catalog models for plugin selection UX."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from aetherflow.core.entitlements import RoleName


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
