"""Plugin trust verification."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from aetherflow.plugins.manifest import PluginDistribution, PluginManifest


@dataclass(frozen=True, slots=True)
class PluginAuthenticodeResult:
    """Result returned by the Authenticode adapter."""

    trusted: bool
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class PluginTrustResult:
    """Final plugin trust decision."""

    trusted: bool
    reason: str | None = None


class PluginAuthenticodeVerifier:
    """Verify native plugin signatures with PowerShell Authenticode checks."""

    def __init__(
        self,
        *,
        runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    ) -> None:
        """Initialize the verifier.

        Args:
            runner: Optional subprocess runner for tests.

        """
        self._runner = runner or subprocess.run

    def verify(self, artifact_path: Path) -> PluginAuthenticodeResult:
        """Verify a native plugin artifact path.

        Args:
            artifact_path: DLL path to validate.

        Returns:
            Authenticode verification result.

        """
        if not artifact_path.exists():
            return PluginAuthenticodeResult(trusted=False, reason='missing-artifact')
        command = [
            'powershell',
            '-NoProfile',
            '-NonInteractive',
            '-Command',
            (
                "Get-AuthenticodeSignature -FilePath "
                f"'{artifact_path}' | "
                "Select-Object Status, StatusMessage, "
                "@{Name='Thumbprint';Expression={$_.SignerCertificate.Thumbprint}} | "
                'ConvertTo-Json -Compress'
            ),
        ]
        try:
            result = self._runner(
                command,
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            return PluginAuthenticodeResult(
                trusted=False,
                reason='verification-error',
            )
        if result.returncode != 0 or not result.stdout:
            return PluginAuthenticodeResult(
                trusted=False,
                reason='verification-error',
            )
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            return PluginAuthenticodeResult(
                trusted=False,
                reason='verification-error',
            )
        status = str(payload.get('Status', '')).lower()
        if status == 'valid':
            return PluginAuthenticodeResult(trusted=True)
        reason_map = {
            'notsigned': 'unsigned',
            'hashmismatch': 'hash-mismatch',
            'nottrusted': 'untrusted-publisher',
            'certificaterevoked': 'revoked',
            'nottimevalid': 'expired',
        }
        return PluginAuthenticodeResult(
            trusted=False,
            reason=reason_map.get(status, 'verification-error'),
        )


class PluginTrustVerifier:
    """Verify plugin trust and compatibility."""

    def __init__(
        self,
        *,
        artifact_verifier: PluginAuthenticodeVerifier | None = None,
    ) -> None:
        """Initialize the trust verifier.

        Args:
            artifact_verifier: Optional Authenticode verifier implementation.

        """
        self._artifact_verifier = artifact_verifier or PluginAuthenticodeVerifier()

    def verify(self, manifest: PluginManifest) -> PluginTrustResult:
        """Return whether a plugin may be considered trusted."""
        if manifest.api_version != '1.0':
            return PluginTrustResult(
                trusted=False,
                reason='unsupported-api-version',
            )
        if manifest.distribution is PluginDistribution.BUILTIN:
            return PluginTrustResult(trusted=True)
        if manifest.artifact_path is None:
            return PluginTrustResult(
                trusted=False,
                reason='missing-artifact-path',
            )
        result = self._artifact_verifier.verify(manifest.artifact_path)
        return PluginTrustResult(trusted=result.trusted, reason=result.reason)
