"""Resource manifest validation helpers."""

from __future__ import annotations

from pathlib import Path

from loguru import logger

from aetherflow.core.oauth import MockOAuthProvider, OAuthProvider
from aetherflow.core.resources_manifest import (
    ManifestValidationResult,
    ResourceManifest,
)
from aetherflow.security.manifest_signing import verify_manifest_signature


class ResourcesClient:
    """Validate signed Online Resources manifests."""

    def __init__(
        self,
        *,
        oauth_provider: OAuthProvider | None = None,
        trust_store_path: Path | None = None,
    ) -> None:
        """Initialize the resources client.

        Args:
            oauth_provider: Optional OAuth provider implementation.
            trust_store_path: Optional detached manifest trust store override.

        """
        self._oauth_provider = oauth_provider or MockOAuthProvider()
        self._trust_store_path = trust_store_path

    def validate_manifest(self, manifest: ResourceManifest) -> ManifestValidationResult:
        """Return whether a resource manifest is trusted."""
        result = manifest.validate()
        if not result.valid:
            logger.warning('Manifest validation failed: {}', result.errors)
            return result

        signature_result = verify_manifest_signature(
            payload=manifest.signed_payload(),
            signature=manifest.signature,
            signing_key_id=manifest.signing_key_id,
            trust_store_path=self._trust_store_path,
        )
        if not signature_result.valid:
            return ManifestValidationResult(
                valid=False,
                errors=['Detached signature verification failed.'],
                reason_codes=(signature_result.reason or 'invalid-signature',),
            )
        return ManifestValidationResult(valid=True, errors=[], reason_codes=())

    def oauth_enabled(self) -> bool:
        """Return whether an OAuth provider is enabled."""
        return self._oauth_provider.is_enabled()
