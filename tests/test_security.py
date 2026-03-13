from __future__ import annotations

from dataclasses import replace

from aetherflow.core.bundle_installer import BundleInstaller, BundleManifest
from aetherflow.plugins.manifest import PluginManifest, PluginType, PluginVersion
from aetherflow.plugins.trust import PluginTrustVerifier


def _valid_plugin_manifest() -> PluginManifest:
    """Build a valid plugin manifest for trust verification tests."""
    return PluginManifest(
        plugin_id='input.xinput',
        name='XInput Provider',
        version=PluginVersion.parse('1.0.0'),
        api_version='1.0',
        plugin_type=PluginType.INPUT,
        entrypoint='aetherflow.input.xinput',
        signed=True,
        premium=False,
        required_entitlements=[],
        requires_worker=False,
        requires_drivers=[],
        signature_scheme='Authenticode',
        digest_algorithm='SHA-256',
        rsa_key_bits=3072,
        publisher_thumbprint='A1B2C3D4',
        trust_root_thumbprint='E5F6A7B8',
        revoked=False,
        expired=False,
        tampered=False,
    )


def test_bundle_installer_rejects_invalid_signature() -> None:
    installer = BundleInstaller()
    manifest = BundleManifest(
        bundle_id='vision.bundle',
        version='1.0.0',
        python_version='3.12',
        dependencies=[],
        sha256='expected',
        signature='invalid',
    )

    result = installer.install(manifest=manifest, archive_hash='expected')

    assert result.state == 'FAILED'
    assert 'signature' in result.logs[-1].lower()


def test_plugin_trust_accepts_valid_manifest() -> None:
    verifier = PluginTrustVerifier()
    manifest = _valid_plugin_manifest()

    assert verifier.verify(manifest) is True


def test_plugin_trust_rejects_unsigned_manifest() -> None:
    verifier = PluginTrustVerifier()
    manifest = replace(_valid_plugin_manifest(), signed=False)

    assert verifier.verify(manifest) is False


def test_plugin_trust_rejects_tampered_manifest() -> None:
    verifier = PluginTrustVerifier()
    manifest = replace(_valid_plugin_manifest(), tampered=True)

    assert verifier.verify(manifest) is False


def test_plugin_trust_rejects_expired_manifest() -> None:
    verifier = PluginTrustVerifier()
    manifest = replace(_valid_plugin_manifest(), expired=True)

    assert verifier.verify(manifest) is False


def test_plugin_trust_rejects_revoked_manifest() -> None:
    verifier = PluginTrustVerifier()
    manifest = replace(_valid_plugin_manifest(), revoked=True)

    assert verifier.verify(manifest) is False


def test_plugin_trust_rejects_scheme_mismatch() -> None:
    verifier = PluginTrustVerifier()
    manifest = replace(_valid_plugin_manifest(), signature_scheme='Other')

    assert verifier.verify(manifest) is False


def test_plugin_trust_rejects_digest_mismatch() -> None:
    verifier = PluginTrustVerifier()
    manifest = replace(_valid_plugin_manifest(), digest_algorithm='SHA-1')

    assert verifier.verify(manifest) is False


def test_plugin_trust_rejects_key_bits_mismatch() -> None:
    verifier = PluginTrustVerifier()
    manifest = replace(_valid_plugin_manifest(), rsa_key_bits=2048)

    assert verifier.verify(manifest) is False


def test_plugin_trust_rejects_missing_thumbprints() -> None:
    verifier = PluginTrustVerifier()
    manifest = replace(_valid_plugin_manifest(), publisher_thumbprint=None)

    assert verifier.verify(manifest) is False


def test_plugin_trust_rejects_api_version_mismatch() -> None:
    verifier = PluginTrustVerifier()
    manifest = replace(_valid_plugin_manifest(), api_version='0.9')

    assert verifier.verify(manifest) is False
