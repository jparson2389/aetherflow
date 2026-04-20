from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path

from aetherflow.plugins.manifest import (
    PluginDistribution,
    PluginManifest,
    PluginType,
    PluginVersion,
)
from aetherflow.plugins.trust import (
    PluginAuthenticodeResult,
    PluginAuthenticodeVerifier,
    PluginTrustVerifier,
)


class StubAuthenticodeVerifier:
    """Return preconfigured Authenticode verification results."""

    def __init__(self, result: PluginAuthenticodeResult) -> None:
        self._result = result

    def verify(self, _artifact_path: Path) -> PluginAuthenticodeResult:
        return self._result


def _completed_process_runner(
    stdout: str,
) -> Callable[..., subprocess.CompletedProcess[str]]:
    """Build a subprocess runner stub for Authenticode JSON payloads."""

    def runner(*args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=stdout,
            stderr='',
        )

    return runner


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
        signed=True,
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


def test_authenticode_verifier_maps_unsigned_status(tmp_path: Path) -> None:
    artifact_path = tmp_path / 'capture.dll'
    artifact_path.write_bytes(b'dll')
    verifier = PluginAuthenticodeVerifier(
        runner=_completed_process_runner(
            '{"Status":1,"StatusMessage":"NotSigned","Thumbprint":null}'
        )
    )

    result = verifier.verify(artifact_path)

    assert result.trusted is False
    assert result.reason == 'unsigned'


def test_authenticode_verifier_maps_untrusted_publisher_status(tmp_path: Path) -> None:
    artifact_path = tmp_path / 'capture.dll'
    artifact_path.write_bytes(b'dll')
    verifier = PluginAuthenticodeVerifier(
        runner=_completed_process_runner(
            '{"Status":3,"StatusMessage":"NotTrusted","Thumbprint":null}'
        )
    )

    result = verifier.verify(artifact_path)

    assert result.trusted is False
    assert result.reason == 'untrusted-publisher'


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


def test_plugin_trust_rejects_tampered_plugin(tmp_path: Path) -> None:
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
        distribution=manifest.distribution,
        artifact_path=manifest.artifact_path,
        premium=manifest.premium,
        required_entitlements=manifest.required_entitlements,
        requires_worker=manifest.requires_worker,
        requires_drivers=manifest.requires_drivers,
        signed=manifest.signed,
        tampered=True,
    )

    result = verifier.verify(manifest)

    assert result.trusted is False
    assert result.reason == 'tampered'


def test_plugin_trust_reports_unsigned_when_manifest_not_signed_and_verifier_fails(
    tmp_path: Path,
) -> None:
    verifier = PluginTrustVerifier(
        artifact_verifier=StubAuthenticodeVerifier(
            PluginAuthenticodeResult(trusted=False, reason='untrusted-publisher')
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
        distribution=manifest.distribution,
        artifact_path=manifest.artifact_path,
        premium=manifest.premium,
        required_entitlements=manifest.required_entitlements,
        requires_worker=manifest.requires_worker,
        requires_drivers=manifest.requires_drivers,
        signed=False,
    )

    result = verifier.verify(manifest)

    assert result.trusted is False
    assert result.reason == 'unsigned'


def test_plugin_trust_rejects_untrusted_publisher(tmp_path: Path) -> None:
    verifier = PluginTrustVerifier(
        artifact_verifier=StubAuthenticodeVerifier(
            PluginAuthenticodeResult(trusted=False, reason='untrusted-publisher')
        )
    )

    result = verifier.verify(_external_plugin_manifest(tmp_path))

    assert result.trusted is False
    assert result.reason == 'untrusted-publisher'


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
