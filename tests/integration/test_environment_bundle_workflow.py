"""Integration tests wiring environment records with bundle install (AF-04-02)."""

from __future__ import annotations

from pathlib import Path

from bundle_manifest_fixtures import build_test_manifest

from aetherflow.core.bundle_installer import BundleInstaller
from aetherflow.core.env_manager import EnvironmentManager, GpuProbeStatus


def test_environment_lifecycle_with_signed_bundle_install(tmp_path: Path) -> None:
    """Env validation succeeds; ambiguous bundle id still installs when signed."""
    manager = EnvironmentManager()
    manager.create('integration-env', python_version='3.12')
    summary = manager.validate(
        'integration-env',
        required_imports={'numpy': True},
        dependency_count=3,
        python_version='3.12',
        gpu_probe_status=GpuProbeStatus.SUPPORTED,
    )
    assert summary['validation_status'] == 'validated'

    archive_path = tmp_path / 'bundle.afbundle'
    archive_path.write_bytes(b'integration-archive')
    trust_store_path = tmp_path / 'trust_store.json'
    installer = BundleInstaller(trust_store_path=trust_store_path)
    manifest = build_test_manifest(
        archive_path=archive_path,
        trust_store_path=trust_store_path,
        bundle_id='vision.unknown',
    )
    result = installer.install(manifest=manifest, archive_path=archive_path)
    assert result.state == 'READY'


def test_bundle_install_rejects_tampered_archive_after_env_created(
    tmp_path: Path,
) -> None:
    """Invalid bundle bytes are rejected after an env record exists (failure coverage)."""
    EnvironmentManager().create('env-with-bad-bundle', python_version='3.12')
    archive_path = tmp_path / 'bundle.afbundle'
    archive_path.write_bytes(b'original')
    trust_store_path = tmp_path / 'trust_store.json'
    installer = BundleInstaller(trust_store_path=trust_store_path)
    manifest = build_test_manifest(
        archive_path=archive_path,
        trust_store_path=trust_store_path,
        bundle_id='vision.bundle',
    )
    archive_path.write_bytes(b'tampered')
    result = installer.install(manifest=manifest, archive_path=archive_path)
    assert result.state == 'FAILED'
    assert result.reason == 'hash-mismatch'
