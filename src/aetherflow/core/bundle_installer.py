"""Signed environment bundle installation helpers."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger

from aetherflow.security.manifest_signing import verify_manifest_signature


def _bundle_signature_payload(manifest: BundleManifest) -> dict[str, object]:
    """Build the signed bundle manifest payload.

    Args:
        manifest: Bundle manifest data.

    Returns:
        Canonicalizable payload without the detached signature field.

    """
    return {
        'archive_size_bytes': manifest.archive_size_bytes,
        'bundle_id': manifest.bundle_id,
        'dependencies': sorted(manifest.dependencies),
        'python_version': manifest.python_version,
        'sha256': manifest.sha256,
        'signing_key_id': manifest.signing_key_id,
        'version': manifest.version,
    }


@dataclass(frozen=True, slots=True)
class BundleManifest:
    """Signed bundle manifest."""

    archive_size_bytes: int
    bundle_id: str
    version: str
    python_version: str
    dependencies: list[str]
    sha256: str
    signing_key_id: str
    signature: str


@dataclass(slots=True)
class BundleInstallResult:
    """Bundle installation result."""

    state: str
    reason: str | None = None
    logs: list[str] = field(default_factory=list)


class BundleInstaller:
    """Validate and stage environment bundle installs."""

    def __init__(self, *, trust_store_path: Path | None = None) -> None:
        """Initialize the bundle installer.

        Args:
            trust_store_path: Optional manifest trust store override.

        """
        self._trust_store_path = trust_store_path

    def verify_signature(self, manifest: BundleManifest) -> BundleInstallResult:
        """Verify a bundle manifest signature.

        Args:
            manifest: Bundle manifest data.

        Returns:
            Result state for the signature verification phase.

        """
        result = verify_manifest_signature(
            payload=_bundle_signature_payload(manifest),
            signature=manifest.signature,
            signing_key_id=manifest.signing_key_id,
            trust_store_path=self._trust_store_path,
        )
        if result.valid:
            return BundleInstallResult(
                state='READY',
                logs=['Signature verified.'],
            )
        return BundleInstallResult(
            state='FAILED',
            reason=result.reason,
            logs=['Signature validation failed.'],
        )

    def install(
        self,
        *,
        manifest: BundleManifest,
        archive_path: Path | bytes,
    ) -> BundleInstallResult:
        """Install a bundle after validating its signature and digest.

        Args:
            manifest: Bundle manifest.
            archive_path: Archive path or raw bytes.

        Returns:
            Installation result state and logs.

        """
        logs = [f'Starting install for {manifest.bundle_id}.']
        logger.debug('Bundle install started for {}.', manifest.bundle_id)
        signature_result = self.verify_signature(manifest)
        if signature_result.state != 'READY':
            logs.extend(signature_result.logs)
            logger.warning('Bundle signature validation failed for {}.', manifest.bundle_id)
            return BundleInstallResult(
                state='FAILED',
                reason=signature_result.reason,
                logs=logs,
            )
        logs.extend(signature_result.logs)
        archive_bytes = (
            archive_path.read_bytes()
            if isinstance(archive_path, Path)
            else archive_path
        )
        archive_hash = hashlib.sha256(archive_bytes).hexdigest()
        if archive_hash != manifest.sha256:
            logs.append('SHA256 mismatch detected.')
            logger.warning('Bundle hash mismatch for {}.', manifest.bundle_id)
            return BundleInstallResult(
                state='FAILED',
                reason='hash-mismatch',
                logs=logs,
            )
        if len(archive_bytes) != manifest.archive_size_bytes:
            logs.append('Archive size mismatch detected.')
            logger.warning('Bundle size mismatch for {}.', manifest.bundle_id)
            return BundleInstallResult(
                state='FAILED',
                reason='size-mismatch',
                logs=logs,
            )
        logs.append('Bundle verified and ready.')
        logger.debug('Bundle install ready for {}.', manifest.bundle_id)
        return BundleInstallResult(state='READY', logs=logs)
