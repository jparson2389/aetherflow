from __future__ import annotations

from pathlib import Path

from aetherflow.plugins.manifest import (
    PluginDistribution,
    PluginManifest,
    PluginType,
    PluginVersion,
)
from aetherflow.plugins.trust import (
    PluginAuthenticodeResult,
    PluginTrustVerifier,
)


class StubAuthenticodeVerifier:
    """Return preconfigured Authenticode verification results."""

    def __init__(self, result: PluginAuthenticodeResult) -> None:
        self._result = result

    def verify(self, artifact_path: Path) -> PluginAuthenticodeResult:
        return self._result


def _external_plugin_manifest(tmp_path: Path) -> PluginManifest:
    """Build a valid external plugin manifest for trust verification tests."""
    artifact_path = tmp_path / 'capture.dll'
    artifact_path.write_bytes(b'dll')
    return PluginManifest(
        plugin_id='input.xinput',
        name='XInput Provider',
        version=PluginVersion.parse('1.0.0'),
        api_version='1.0',
        plugin_type=PluginType.INPUT,
        entrypoint='capture.dll',
        artifact_path=artifact_path,
        distribution=PluginDistribution.EXTERNAL,
        premium=False,
        required_entitlements=[],
        requires_worker=False,
        requires_drivers=[],
    )


def test_plugin_trust_accepts_valid_external_plugin(tmp_path: Path) -> None:
    verifier = PluginTrustVerifier(
        artifact_verifier=StubAuthenticodeVerifier(
            PluginAuthenticodeResult(trusted=True)
        )
    )

    result = verifier.verify(_external_plugin_manifest(tmp_path))

    assert result.trusted is True
    assert result.reason is None


def test_plugin_trust_rejects_missing_artifact_path(tmp_path: Path) -> None:
    verifier = PluginTrustVerifier(
        artifact_verifier=StubAuthenticodeVerifier(
            PluginAuthenticodeResult(trusted=True)
        )
    )
    manifest = _external_plugin_manifest(tmp_path)
    manifest = PluginManifest(
        plugin_id=manifest.plugin_id,
        name=manifest.name,
        version=manifest.version,
        api_version=manifest.api_version,
        plugin_type=manifest.plugin_type,
        entrypoint=manifest.entrypoint,
        distribution=PluginDistribution.EXTERNAL,
        artifact_path=None,
        premium=manifest.premium,
        required_entitlements=manifest.required_entitlements,
        requires_worker=manifest.requires_worker,
        requires_drivers=manifest.requires_drivers,
    )

    result = verifier.verify(manifest)

    assert result.trusted is False
    assert result.reason == 'missing-artifact-path'


def test_plugin_trust_rejects_revoked_plugin(tmp_path: Path) -> None:
    verifier = PluginTrustVerifier(
        artifact_verifier=StubAuthenticodeVerifier(
            PluginAuthenticodeResult(trusted=False, reason='revoked')
        )
    )

    result = verifier.verify(_external_plugin_manifest(tmp_path))

    assert result.trusted is False
    assert result.reason == 'revoked'


def test_plugin_trust_rejects_api_version_mismatch(tmp_path: Path) -> None:
    verifier = PluginTrustVerifier(
        artifact_verifier=StubAuthenticodeVerifier(
            PluginAuthenticodeResult(trusted=True)
        )
    )
    manifest = _external_plugin_manifest(tmp_path)
    manifest = PluginManifest(
        plugin_id=manifest.plugin_id,
        name=manifest.name,
        version=manifest.version,
        api_version='0.9',
        plugin_type=manifest.plugin_type,
        entrypoint=manifest.entrypoint,
        distribution=manifest.distribution,
        artifact_path=manifest.artifact_path,
        premium=manifest.premium,
        required_entitlements=manifest.required_entitlements,
        requires_worker=manifest.requires_worker,
        requires_drivers=manifest.requires_drivers,
    )

    result = verifier.verify(manifest)

    assert result.trusted is False
    assert result.reason == 'unsupported-api-version'
