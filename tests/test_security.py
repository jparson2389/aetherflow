from aetherflow.core.bundle_installer import BundleInstaller, BundleManifest


def test_bundle_installer_rejects_invalid_signature() -> None:
    installer = BundleInstaller()
    manifest = BundleManifest(
        bundle_id="vision.bundle",
        version="1.0.0",
        python_version="3.12",
        dependencies=[],
        sha256="expected",
        signature="invalid",
    )

    result = installer.install(manifest=manifest, archive_hash="expected")

    assert result.state == "FAILED"
    assert "signature" in result.logs[-1].lower()
