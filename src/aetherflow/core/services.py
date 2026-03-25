"""Service container helpers for the Aetherflow host."""

from __future__ import annotations

from dataclasses import dataclass

from loguru import logger

from aetherflow.core.entitlements import EntitlementStore, RoleName, UserRole
from aetherflow.core.profile_persistence import ProfileRepository
from aetherflow.core.profiles import ProfileStore
from aetherflow.core.settings import AetherflowSettings
from aetherflow.plugins.trust import PluginTrustVerifier


@dataclass(slots=True)
class AppServices:
    """Shared runtime services exposed to plugins and UI code."""

    entitlements: EntitlementStore
    trust_verifier: PluginTrustVerifier
    roles: list[UserRole]
    profile_store: ProfileStore
    profile_repo: ProfileRepository


def create_default_services(
    *,
    roles: list[UserRole] | None = None,
) -> AppServices:
    """Create the default service container.

    Args:
        roles: Optional role set for the active user session.

    Returns:
        An initialized service container.

    """
    resolved_roles = roles or [UserRole(name=RoleName.POWER_GAMER)]
    logger.debug('Creating default application services.')
    settings = AetherflowSettings()
    profile_repo = ProfileRepository(path=settings.input_profiles_path)
    profile_store = profile_repo.load()
    return AppServices(
        entitlements=EntitlementStore(),
        trust_verifier=PluginTrustVerifier(),
        roles=resolved_roles,
        profile_store=profile_store,
        profile_repo=profile_repo,
    )
