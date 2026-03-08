from aetherflow.core.bundle_installer import BundleInstaller, BundleManifest


def test_bundle_installer_rejects_hash_mismatch() -> None:
    installer = BundleInstaller()
    manifest = BundleManifest(
        bundle_id="vision.bundle",
        version="1.0.0",
        python_version="3.12",
        dependencies=["opencv-python==4.13.0.92"],
        sha256="expected",
        signature="valid-signature",
    )

    result = installer.install(manifest=manifest, archive_hash="wrong")

    assert result.state == "FAILED"
    assert "sha256 mismatch" in result.logs[-1].lower()
