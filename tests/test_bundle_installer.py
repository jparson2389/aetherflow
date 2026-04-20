from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict

from bundle_manifest_fixtures import build_test_manifest

from aetherflow.core.bundle_installer import (
    BundleInstaller,
    BundleInstallResult,
    BundleManifest,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class BundleInstallReport(TypedDict):
    """Typed bundle install report payload."""

    total: int
    successes: int
    failures: int
    success_rate: float
    generated_at_utc: str


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
    manifest = build_test_manifest(
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
    manifest = build_test_manifest(
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
    manifest = build_test_manifest(
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
        manifest = build_test_manifest(
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
