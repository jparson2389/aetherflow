from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict

from aetherflow.core.bundle_installer import (
    BundleInstaller,
    BundleInstallResult,
    BundleManifest,
    compute_bundle_signature,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class BundleInstallReport(TypedDict):
    """Typed bundle install report payload."""

    total: int
    successes: int
    failures: int
    success_rate: float
    generated_at_utc: str


def _build_manifest(
    *,
    bundle_id: str,
    version: str = '1.0.0',
    python_version: str = '3.12',
    dependencies: list[str] | None = None,
    sha256: str = 'expected',
) -> BundleManifest:
    """Build a bundle manifest with a deterministic signature."""
    deps = dependencies or []
    unsigned = BundleManifest(
        bundle_id=bundle_id,
        version=version,
        python_version=python_version,
        dependencies=deps,
        sha256=sha256,
        signature='',
    )
    signature = compute_bundle_signature(unsigned)
    return BundleManifest(
        bundle_id=bundle_id,
        version=version,
        python_version=python_version,
        dependencies=deps,
        sha256=sha256,
        signature=signature,
    )


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


def test_bundle_installer_rejects_hash_mismatch() -> None:
    installer = BundleInstaller()
    manifest = _build_manifest(
        bundle_id='vision.bundle',
        dependencies=['opencv-python==4.13.0.92'],
    )

    result = installer.install(manifest=manifest, archive_hash='wrong')

    assert result.state == 'FAILED'
    assert 'sha256 mismatch' in result.logs[-1].lower()


def test_bundle_installer_accepts_ambiguous_extension() -> None:
    installer = BundleInstaller()
    manifest = _build_manifest(bundle_id='vision.unknown')

    result = installer.install(manifest=manifest, archive_hash=manifest.sha256)

    assert result.state == 'READY'
    assert result.logs[-1].lower().startswith('bundle verified')


def test_bundle_installer_generates_report(bundle_install_count: int) -> None:
    report_path = PROJECT_ROOT / 'logs' / 'bundle_install_report.json'
    if report_path.exists():
        report_path.unlink()

    installer = BundleInstaller()
    results = []
    for idx in range(bundle_install_count):
        manifest = _build_manifest(
            bundle_id=f'vision.bundle.{idx}',
            sha256=f'hash-{idx}',
        )
        results.append(
            installer.install(manifest=manifest, archive_hash=manifest.sha256),
        )

    report = _write_report(results=results, report_path=report_path)

    assert report_path.exists()
    assert report['success_rate'] >= 0.95
