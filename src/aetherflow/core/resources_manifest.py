"""Signed resource manifest models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ResourceEntry:
    """Single installable resource entry."""

    resource_id: str
    kind: str
    version: str
    sha256: str
    size: int
    premium: bool
    required_tier: str | None = None


@dataclass(frozen=True, slots=True)
class ResourceManifest:
    """Manifest envelope for resource catalog payloads."""

    version: str
    signature: str
    resources: list[ResourceEntry] = field(default_factory=list)
