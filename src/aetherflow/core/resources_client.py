"""Resource manifest validation helpers."""

from __future__ import annotations

from aetherflow.core.oauth import MockOAuthProvider, OAuthProvider
from aetherflow.core.resources_manifest import ResourceManifest


class ResourcesClient:
    """Validate signed Online Resources manifests."""

    required_signature_scheme = "Authenticode"
    required_digest_algorithm = "SHA-256"
    required_rsa_key_bits = 3072

    def __init__(self, *, oauth_provider: OAuthProvider | None = None) -> None:
        """Initialize the resources client.

        Args:
            oauth_provider: Optional OAuth provider implementation.

        """
        self._oauth_provider = oauth_provider or MockOAuthProvider()

    def validate_manifest(self, manifest: ResourceManifest) -> bool:
        """Return whether a resource manifest is trusted."""
        if manifest.signature != "valid":
            return False
        if manifest.signature_scheme != self.required_signature_scheme:
            return False
        if manifest.digest_algorithm != self.required_digest_algorithm:
            return False
        if manifest.rsa_key_bits != self.required_rsa_key_bits:
            return False
        if not manifest.publisher_thumbprint or not manifest.trust_root_thumbprint:
            return False
        return True

    def oauth_enabled(self) -> bool:
        """Return whether an OAuth provider is enabled."""
        return self._oauth_provider.is_enabled()
