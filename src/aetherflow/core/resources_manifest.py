"""Signed resource manifest models."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from loguru import logger

_SHA256_RE = re.compile(r'^[0-9a-f]{64}$')


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
    signature_scheme: str | None = None
    digest_algorithm: str | None = None
    rsa_key_bits: int | None = None
    publisher_thumbprint: str | None = None
    trust_root_thumbprint: str | None = None
    resources: list[ResourceEntry] = field(default_factory=list)

    def validate(self, policy: SignaturePolicy) -> ManifestValidationResult:
        """Validate the manifest using policy-only rules.

        Args:
            policy: Signature policy requirements.

        Returns:
            Validation result containing errors, if any.

        """
        errors: list[str] = []
        if not self.signature:
            errors.append('Missing signature value.')
        if self.signature_scheme != policy.signature_scheme:
            errors.append('Signature scheme mismatch.')
        if self.digest_algorithm != policy.digest_algorithm:
            errors.append('Digest algorithm mismatch.')
        if self.rsa_key_bits != policy.rsa_key_bits:
            errors.append('RSA key size mismatch.')
        if policy.require_thumbprints:
            if not self.publisher_thumbprint:
                errors.append('Missing publisher thumbprint.')
            if not self.trust_root_thumbprint:
                errors.append('Missing trust root thumbprint.')
        for entry in self.resources:
            if entry.size < 0:
                errors.append(f'Negative size for {entry.resource_id}.')
            if not _SHA256_RE.match(entry.sha256.lower()):
                errors.append(f'Invalid sha256 for {entry.resource_id}.')
            if entry.premium and not entry.required_tier:
                errors.append(f'Missing required tier for {entry.resource_id}.')
        if errors:
            logger.debug('Manifest validation errors: {}', errors)
        return ManifestValidationResult(valid=not errors, errors=errors)


@dataclass(frozen=True, slots=True)
class SignaturePolicy:
    """Signature policy for resource manifests."""

    signature_scheme: str
    digest_algorithm: str
    rsa_key_bits: int
    require_thumbprints: bool = True


@dataclass(frozen=True, slots=True)
class ManifestValidationResult:
    """Validation result for resource manifests."""

    valid: bool
    errors: list[str]
