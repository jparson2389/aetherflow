"""Plugin trust verification."""

from __future__ import annotations

from aetherflow.plugins.manifest import PluginManifest


class PluginTrustVerifier:
    """Verify plugin trust and compatibility."""

    required_signature_scheme = 'Authenticode'
    required_digest_algorithm = 'SHA-256'
    required_rsa_key_bits = 3072

    def verify(self, manifest: PluginManifest) -> bool:
        """Return whether a plugin may be considered trusted."""
        if not manifest.signed:
            return False
        if manifest.tampered or manifest.expired or manifest.revoked:
            return False
        if manifest.signature_scheme != self.required_signature_scheme:
            return False
        if manifest.digest_algorithm != self.required_digest_algorithm:
            return False
        if manifest.rsa_key_bits != self.required_rsa_key_bits:
            return False
        if not manifest.publisher_thumbprint or not manifest.trust_root_thumbprint:
            return False
        return manifest.api_version == '1.0'
