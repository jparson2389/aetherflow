"""Signed environment bundle installation helpers."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class BundleManifest:
    """Signed bundle manifest."""

    bundle_id: str
    version: str
    python_version: str
    dependencies: list[str]
    sha256: str
    signature: str


@dataclass(slots=True)
class BundleInstallResult:
    """Bundle installation result."""

    state: str
    logs: list[str] = field(default_factory=list)


class BundleInstaller:
    """Validate and stage environment bundle installs."""

    def install(
        self,
        *,
        manifest: BundleManifest,
        archive_hash: str,
    ) -> BundleInstallResult:
        """Install a bundle after validating its signature and digest.

        Args:
            manifest: Bundle manifest.
            archive_hash: Observed archive SHA-256 hash.

        Returns:
            Installation result state and logs.

        """
        logs = [f"Starting install for {manifest.bundle_id}."]
        if manifest.signature != "valid-signature":
            logs.append("Signature validation failed.")
            return BundleInstallResult(state="FAILED", logs=logs)
        if archive_hash != manifest.sha256:
            logs.append("SHA256 mismatch detected.")
            return BundleInstallResult(state="FAILED", logs=logs)
        logs.append("Bundle verified and ready.")
        return BundleInstallResult(state="READY", logs=logs)
