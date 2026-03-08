"""Entitlement and role models for premium gating."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class EntitlementState(str, Enum):
    """Supported entitlement states for plugin gating."""

    LOADED = "LOADED"
    ELIGIBLE = "ELIGIBLE"
    LOCKED = "LOCKED"
    GRACE = "GRACE"


class RoleName(str, Enum):
    """Role names defined by the PRD."""

    POWER_GAMER = "power_gamer"
    VISION_ML_TINKERER = "vision_ml_tinkerer"
    ACCESSIBILITY_MODDER = "accessibility_modder"
    ADMIN_OPERATOR = "admin_operator"


ROLE_CAPABILITIES: dict[RoleName, tuple[str, ...]] = {
    RoleName.POWER_GAMER: ("profile.manage", "mapping.use", "profiles.switch"),
    RoleName.VISION_ML_TINKERER: (
        "profile.manage",
        "mapping.use",
        "capture.configure",
        "env.manage",
        "resources.install",
    ),
    RoleName.ACCESSIBILITY_MODDER: (
        "profile.manage",
        "mapping.use",
        "automation.calibrate",
        "scripts.manage",
    ),
    RoleName.ADMIN_OPERATOR: (
        "profile.manage",
        "mapping.use",
        "capture.configure",
        "env.manage",
        "resources.install",
        "admin.manage_users",
        "admin.audit",
        "entitlements.assign",
    ),
}


@dataclass(frozen=True, slots=True)
class UserRole:
    """Role information for the active session."""

    name: RoleName
    capabilities: tuple[str, ...] = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "capabilities", ROLE_CAPABILITIES[self.name])


class EntitlementStore:
    """Evaluate premium access for plugins and resources."""

    def __init__(self) -> None:
        """Initialize empty entitlement and grace caches."""
        self._entitlements: dict[str, set[str]] = {}
        self._grace_entitlements: dict[str, set[str]] = {}

    def grant(self, plugin_id: str, required_entitlements: tuple[str, ...]) -> None:
        """Grant the required entitlements for a premium plugin.

        Args:
            plugin_id: Plugin or resource identifier.
            required_entitlements: Required entitlement names.

        """
        self._entitlements[plugin_id] = set(required_entitlements)

    def activate_grace(
        self,
        plugin_id: str,
        required_entitlements: tuple[str, ...],
    ) -> None:
        """Enable grace-period access for a premium plugin.

        Args:
            plugin_id: Plugin or resource identifier.
            required_entitlements: Required entitlement names.

        """
        self._grace_entitlements[plugin_id] = set(required_entitlements)

    def evaluate(
        self,
        plugin_id: str,
        required_entitlements: tuple[str, ...],
    ) -> EntitlementState:
        """Evaluate entitlement state for a plugin.

        Args:
            plugin_id: Plugin or resource identifier.
            required_entitlements: Required entitlement names.

        Returns:
            The resolved entitlement state.

        """
        if not required_entitlements:
            return EntitlementState.LOADED
        required = set(required_entitlements)
        granted = self._entitlements.get(plugin_id, set())
        if required.issubset(granted):
            return EntitlementState.LOADED
        grace = self._grace_entitlements.get(plugin_id, set())
        if required.issubset(grace):
            return EntitlementState.GRACE
        return EntitlementState.LOCKED
