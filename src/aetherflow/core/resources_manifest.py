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
    signing_key_id: str = ''
    signature_scheme: str | None = None
    digest_algorithm: str | None = None
    rsa_key_bits: int | None = None
    publisher_thumbprint: str | None = None
    trust_root_thumbprint: str | None = None
    resources: list[ResourceEntry] = field(default_factory=list)

    def signed_payload(self) -> dict[str, object]:
        """Return the payload covered by the detached signature.

        Returns:
            Canonicalizable payload without the signature field.

        """
        return {
            'resources': [
                {
                    'kind': entry.kind,
                    'premium': entry.premium,
                    'required_tier': entry.required_tier,
                    'resource_id': entry.resource_id,
                    'sha256': entry.sha256,
                    'size': entry.size,
                    'version': entry.version,
                }
                for entry in self.resources
            ],
            'signing_key_id': self.signing_key_id,
            'version': self.version,
        }

    def validate(
        self, _policy: SignaturePolicy | None = None
    ) -> ManifestValidationResult:
        """Validate the manifest structure before trust verification.

        Args:
            policy: Unused legacy compatibility argument.

        Returns:
            Validation result containing errors, if any.

        """
        errors: list[str] = []
        reason_codes: list[str] = []
        if not self.signature:
            errors.append('Missing signature value.')
            reason_codes.append('missing-signature')
        if not self.signing_key_id:
            errors.append('Missing signing key id.')
            reason_codes.append('missing-signing-key-id')
        for entry in self.resources:
            if entry.size < 0:
                errors.append(f'Negative size for {entry.resource_id}.')
                reason_codes.append('negative-size')
            if not _SHA256_RE.match(entry.sha256.lower()):
                errors.append(f'Invalid sha256 for {entry.resource_id}.')
                reason_codes.append('invalid-sha256')
            if entry.premium and not entry.required_tier:
                errors.append(f'Missing required tier for {entry.resource_id}.')
                reason_codes.append('missing-required-tier')
        if errors:
            logger.debug('Manifest validation errors: {}', errors)
        return ManifestValidationResult(
            valid=not errors,
            errors=errors,
            reason_codes=tuple(dict.fromkeys(reason_codes)),
        )


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
    reason_codes: tuple[str, ...] = ()
