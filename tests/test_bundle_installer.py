from __future__ import annotations

import json
from base64 import b64encode
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from aetherflow.core.bundle_installer import (
    BundleInstaller,
    BundleInstallResult,
    BundleManifest,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_KEY_ID = 'test-key-1'
TEST_PRIVATE_KEY_BYTES = bytes(range(1, 33))


class BundleInstallReport(TypedDict):
    """Typed bundle install report payload."""

    total: int
    successes: int
    failures: int
    success_rate: float
    generated_at_utc: str


def _build_manifest(
    *,
    archive_path: Path,
    trust_store_path: Path,
    bundle_id: str,
    version: str = '1.0.0',
    python_version: str = '3.12',
    dependencies: list[str] | None = None,
) -> BundleManifest:
    """Build a signed bundle manifest for an on-disk archive."""
    deps = dependencies or []
    archive_bytes = archive_path.read_bytes()
    unsigned = {
        'archive_size_bytes': len(archive_bytes),
        'bundle_id': bundle_id,
        'dependencies': sorted(deps),
        'version': version,
        'python_version': python_version,
        'sha256': __import__('hashlib').sha256(archive_bytes).hexdigest(),
        'signing_key_id': TEST_KEY_ID,
    }
    private_key = Ed25519PrivateKey.from_private_bytes(TEST_PRIVATE_KEY_BYTES)
    signature = b64encode(
        private_key.sign(
            json.dumps(unsigned, separators=(',', ':'), sort_keys=True).encode('utf-8')
        )
    ).decode('ascii')
    _write_trust_store(trust_store_path)
    return BundleManifest(
        archive_size_bytes=unsigned['archive_size_bytes'],
        bundle_id=bundle_id,
        dependencies=deps,
        sha256=unsigned['sha256'],
        signature=signature,
        signing_key_id=TEST_KEY_ID,
        version=version,
        python_version=python_version,
    )


def _write_trust_store(path: Path) -> None:
    """Persist the public manifest signing key used in tests."""
    public_key = (
        Ed25519PrivateKey.from_private_bytes(TEST_PRIVATE_KEY_BYTES)
        .public_key()
        .public_bytes_raw()
    )
    payload = {
        'active_key_id': TEST_KEY_ID,
        'keys': [
            {
                'key_id': TEST_KEY_ID,
                'algorithm': 'ed25519',
                'public_key': b64encode(public_key).decode('ascii'),
            }
        ],
    }
    path.write_text(json.dumps(payload, indent=2), encoding='utf-8')


def _write_report(
    *,
    results: list[BundleInstallResult],
    report_path: Path,
) -> BundleInstallReport:
    """Persist the bundle install report artifact."""
    total = len(results)
    successes = sum(1 for result in results if result.state == 'READY')
    failures = total - successes
    success_rate = successes / total if total else 0.0
    report: BundleInstallReport = {
        'total': total,
        'successes': successes,
        'failures': failures,
        'success_rate': success_rate,
        'generated_at_utc': datetime.now(tz=UTC).isoformat(),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


def test_bundle_installer_rejects_digest_mismatch(tmp_path: Path) -> None:
    archive_path = tmp_path / 'bundle.afbundle'
    archive_path.write_bytes(b'expected-archive')
    trust_store_path = tmp_path / 'trust_store.json'
    installer = BundleInstaller(trust_store_path=trust_store_path)
    manifest = _build_manifest(
        archive_path=archive_path,
        trust_store_path=trust_store_path,
        bundle_id='vision.bundle',
        dependencies=['opencv-python==4.13.0.92'],
    )
    archive_path.write_bytes(b'tampered-archive')

    result = installer.install(manifest=manifest, archive_path=archive_path)

    assert result.state == 'FAILED'
    assert result.reason == 'hash-mismatch'


def test_bundle_installer_rejects_unknown_signing_key(tmp_path: Path) -> None:
    archive_path = tmp_path / 'bundle.afbundle'
    archive_path.write_bytes(b'archive')
    trust_store_path = tmp_path / 'trust_store.json'
    installer = BundleInstaller(trust_store_path=trust_store_path)
    manifest = _build_manifest(
        archive_path=archive_path,
        trust_store_path=trust_store_path,
        bundle_id='vision.bundle',
    )
    manifest = BundleManifest(
        archive_size_bytes=manifest.archive_size_bytes,
        bundle_id=manifest.bundle_id,
        dependencies=manifest.dependencies,
        python_version=manifest.python_version,
        sha256=manifest.sha256,
        signature=manifest.signature,
        signing_key_id='unknown',
        version=manifest.version,
    )

    result = installer.install(manifest=manifest, archive_path=archive_path)

    assert result.state == 'FAILED'
    assert result.reason == 'unknown-signing-key'


def test_bundle_installer_accepts_signed_archive(tmp_path: Path) -> None:
    archive_path = tmp_path / 'bundle.afbundle'
    archive_path.write_bytes(b'archive')
    trust_store_path = tmp_path / 'trust_store.json'
    installer = BundleInstaller(trust_store_path=trust_store_path)
    manifest = _build_manifest(
        archive_path=archive_path,
        trust_store_path=trust_store_path,
        bundle_id='vision.unknown',
    )

    result = installer.install(manifest=manifest, archive_path=archive_path)

    assert result.state == 'READY'
    assert result.reason is None
    assert result.logs[-1].lower().startswith('bundle verified')


def test_bundle_installer_generates_report(
    bundle_install_count: int,
    tmp_path: Path,
) -> None:
    report_path = PROJECT_ROOT / 'logs' / 'bundle_install_report.json'
    if report_path.exists():
        report_path.unlink()

    trust_store_path = tmp_path / 'trust_store.json'
    installer = BundleInstaller(trust_store_path=trust_store_path)
    results = []
    for idx in range(bundle_install_count):
        archive_path = tmp_path / f'vision.bundle.{idx}.afbundle'
        archive_path.write_bytes(f'archive-{idx}'.encode())
        manifest = _build_manifest(
            archive_path=archive_path,
            trust_store_path=trust_store_path,
            bundle_id=f'vision.bundle.{idx}',
        )
        results.append(
            installer.install(manifest=manifest, archive_path=archive_path),
        )

    report = _write_report(results=results, report_path=report_path)

    assert report_path.exists()
    assert report['success_rate'] >= 0.95
