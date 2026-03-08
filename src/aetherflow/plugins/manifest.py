"""Plugin manifest models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class PluginType(StrEnum):
    """Supported plugin categories."""

    INPUT = "input"
    OUTPUT = "output"
    CAPTURE = "capture"
    DISPLAY = "display"
    WORKER = "worker"
    RESOURCE = "resource"


@dataclass(frozen=True, slots=True)
class PluginVersion:
    """Semantic version value object."""

    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, raw: str) -> PluginVersion:
        """Parse a semantic version string."""
        major, minor, patch = (int(part) for part in raw.split("."))
        return cls(major=major, minor=minor, patch=patch)

    def __str__(self) -> str:
        """Return the dotted semantic version."""
        return f"{self.major}.{self.minor}.{self.patch}"


@dataclass(frozen=True, slots=True)
class PluginManifest:
    """Manifest for a single plugin."""

    plugin_id: str
    name: str
    version: PluginVersion
    api_version: str
    plugin_type: PluginType
    entrypoint: str
    signed: bool
    premium: bool
    required_entitlements: list[str]
    requires_worker: bool
    signature_scheme: str | None = None
    digest_algorithm: str | None = None
    rsa_key_bits: int | None = None
    publisher_thumbprint: str | None = None
    trust_root_thumbprint: str | None = None
    revoked: bool = False
    expired: bool = False
    tampered: bool = False
