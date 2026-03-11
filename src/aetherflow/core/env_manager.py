"""Environment management state."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class GpuProbeStatus(StrEnum):
    """GPU probe status values."""

    NOT_RUN = 'not-run'
    SUPPORTED = 'supported'
    UNSUPPORTED = 'unsupported'
    ERROR = 'error'


@dataclass(slots=True)
class EnvironmentRecord:
    """Environment metadata shown in the UI."""

    name: str
    python_version: str
    dependency_count: int = 0
    disk_usage_mb: int = 0
    validation_status: str = 'pending'
    missing_imports: list[str] = field(default_factory=list)
    gpu_probe_status: GpuProbeStatus = GpuProbeStatus.NOT_RUN


class EnvironmentManager:
    """Manage named Python environments."""

    def __init__(self) -> None:
        """Initialize an empty environment registry."""
        self._records: dict[str, EnvironmentRecord] = {}

    def create(self, name: str, *, python_version: str) -> EnvironmentRecord:
        """Create a new environment record.

        Args:
            name: Environment display name.
            python_version: Target Python version.

        Returns:
            The created environment record.

        """
        record = EnvironmentRecord(name=name, python_version=python_version)
        self._records[name] = record
        return record

    def repair(self, name: str) -> EnvironmentRecord:
        """Mark an environment as repaired."""
        record = self._records[name]
        record.validation_status = 'repaired'
        return record

    def recreate(self, name: str, *, python_version: str) -> EnvironmentRecord:
        """Delete and recreate an environment record."""
        self._records.pop(name, None)
        return self.create(name, python_version=python_version)

    def delete(self, name: str) -> None:
        """Delete an environment record."""
        self._records.pop(name, None)

    def list_names(self) -> list[str]:
        """Return the known environment names."""
        return list(self._records)

    def validate(
        self,
        name: str,
        *,
        required_imports: dict[str, bool],
        dependency_count: int,
        python_version: str,
        gpu_probe_status: GpuProbeStatus,
    ) -> dict[str, object]:
        """Validate environment metadata and capture probe results."""
        record = self._records[name]
        missing = [key for key, ok in required_imports.items() if not ok]
        record.missing_imports = missing
        record.dependency_count = dependency_count
        record.python_version = python_version
        record.gpu_probe_status = gpu_probe_status
        record.validation_status = 'failed' if missing else 'validated'
        return self.summary(name)

    def summary(self, name: str) -> dict[str, str | int]:
        """Return a UI-friendly environment summary."""
        record = self._records[name]
        return {
            'name': record.name,
            'python_version': record.python_version,
            'dependency_count': record.dependency_count,
            'validation_status': record.validation_status,
            'missing_imports': list(record.missing_imports),
            'gpu_probe_status': record.gpu_probe_status.value,
        }
