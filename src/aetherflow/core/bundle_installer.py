"""Signed environment bundle installation helpers."""

from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass, field

from loguru import logger

SIGNATURE_PREFIX = 'sha256:'


def _canonical_manifest_payload(manifest: BundleManifest) -> str:
    """Build a canonical payload for manifest signature verification.

    Args:
        manifest: Bundle manifest data.

    Returns:
        Canonical JSON payload string.

    """
    payload = {
        'bundle_id': manifest.bundle_id,
        'version': manifest.version,
        'python_version': manifest.python_version,
        'dependencies': sorted(manifest.dependencies),
        'sha256': manifest.sha256,
    }
    return json.dumps(payload, separators=(',', ':'), sort_keys=True)


def compute_bundle_signature(manifest: BundleManifest) -> str:
    """Compute the SHA-256 signature for a bundle manifest.

    Args:
        manifest: Bundle manifest data.

    Returns:
        Hex-encoded SHA-256 signature.

    """
    payload = _canonical_manifest_payload(manifest).encode('utf-8')
    return hashlib.sha256(payload).hexdigest()


def _normalize_signature(signature: str) -> str:
    """Normalize a signature string for comparison.

    Args:
        signature: Raw signature string.

    Returns:
        Lowercased hex digest with any scheme prefix removed.

    """
    value = signature.strip()
    if value.lower().startswith(SIGNATURE_PREFIX):
        value = value[len(SIGNATURE_PREFIX) :]
    return value.lower()


@dataclass(frozen=True, slots=True)
class BundleManifest:
    """Signed bundle manifest."""

    bundle_id: str
    version: str
    python_version: str
    dependencies: list[str]
    sha256: str
    signature: str


@dataclass(slots=True)
class BundleInstallResult:
    """Bundle installation result."""

    state: str
    logs: list[str] = field(default_factory=list)


class BundleInstaller:
    """Validate and stage environment bundle installs."""

    def verify_signature(self, manifest: BundleManifest) -> bool:
        """Verify a bundle manifest signature.

        Args:
            manifest: Bundle manifest data.

        Returns:
            True when the signature is valid.

        """
        expected = compute_bundle_signature(manifest)
        provided = _normalize_signature(manifest.signature)
        if not provided:
            return False
        return secrets.compare_digest(provided, expected)

    def install(
        self,
        *,
        manifest: BundleManifest,
        archive_hash: str,
    ) -> BundleInstallResult:
        """Install a bundle after validating its signature and digest.

        Args:
            manifest: Bundle manifest.
            archive_hash: Observed archive SHA-256 hash.

        Returns:
            Installation result state and logs.

        """
        logs = [f'Starting install for {manifest.bundle_id}.']
        logger.debug('Bundle install started for {}.', manifest.bundle_id)
        if not self.verify_signature(manifest):
            logs.append('Signature validation failed.')
            logger.warning('Bundle signature validation failed for {}.', manifest.bundle_id)
            return BundleInstallResult(state='FAILED', logs=logs)
        logs.append('Signature verified.')
        if archive_hash != manifest.sha256:
            logs.append('SHA256 mismatch detected.')
            logger.warning('Bundle hash mismatch for {}.', manifest.bundle_id)
            return BundleInstallResult(state='FAILED', logs=logs)
        logs.append('Bundle verified and ready.')
        logger.debug('Bundle install ready for {}.', manifest.bundle_id)
        return BundleInstallResult(state='READY', logs=logs)
