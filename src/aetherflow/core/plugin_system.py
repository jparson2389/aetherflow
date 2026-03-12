"""Thin Python mirror of the frozen native plugin ABI.

This module exists to give contract tests and Python-side orchestration a stable
view of the Phase 0 plugin ABI without duplicating the richer runtime behavior
implemented in ``aetherflow.plugins``.
"""

from __future__ import annotations

from dataclasses import dataclass

from aetherflow.core.runtime_state import RuntimeState


@dataclass(frozen=True, slots=True)
class Plugin:
    """Mirror the Phase 0 native ``Plugin`` contract.

    Attributes:
        plugin_id: Stable plugin identifier.
        name: Human-readable plugin name.
        version: Plugin version string.
        api_version: ABI/API version expected by the host.
        plugin_type: Plugin category identifier.
        required_entitlements: Entitlements required before activation.
        requires_drivers: Driver dependencies required by the plugin.
        requires_worker: Whether the plugin needs an out-of-process worker.

    """

    plugin_id: str
    name: str
    version: str
    api_version: str
    plugin_type: str
    required_entitlements: list[str]
    requires_drivers: list[str]
    requires_worker: bool


REQUIRED_SIGNATURE_SCHEME = 'Authenticode'
REQUIRED_DIGEST_ALGORITHM = 'SHA-256'
REQUIRED_RSA_KEY_BITS = 3072


@dataclass(frozen=True, slots=True)
class PluginIdentity:
    """Mirror the native PluginIdentity ABI."""

    plugin_id: str
    name: str
    version: str
    api_version: str
    plugin_type: str


@dataclass(frozen=True, slots=True)
class PluginPolicy:
    """Mirror the native PluginPolicy ABI."""

    required_entitlements: str
    requires_drivers: str
    requires_worker: bool
    premium: bool


@dataclass(frozen=True, slots=True)
class SignaturePolicy:
    """Mirror the native SignaturePolicy ABI."""

    signature_scheme: str
    digest_algorithm: str
    rsa_key_bits: int
    publisher_thumbprint: str
    trust_root_thumbprint: str
    require_publisher_chain: bool


@dataclass(frozen=True, slots=True)
class PluginLoadDecision:
    """Mirror the native PluginLoadDecision ABI."""

    runtime_state: RuntimeState
    allow_process_load: bool
    allow_registration: bool
    denial_reason: str


__all__ = [
    'REQUIRED_DIGEST_ALGORITHM',
    'REQUIRED_RSA_KEY_BITS',
    'REQUIRED_SIGNATURE_SCHEME',
    'Plugin',
    'PluginIdentity',
    'PluginLoadDecision',
    'PluginPolicy',
    'RuntimeState',
    'SignaturePolicy',
]
