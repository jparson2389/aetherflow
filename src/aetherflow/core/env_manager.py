"""Environment management state."""

from __future__ import annotations

import logging
import shutil
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

_logger = logging.getLogger(__name__)


class GpuProbeStatus(StrEnum):
    """GPU probe status values."""

    NOT_RUN = 'not-run'
    SUPPORTED = 'supported'
    UNSUPPORTED = 'unsupported'
    ERROR = 'error'


def _validate_env_name(name: str) -> None:
    """Reject environment names that could escape the managed root.

    Args:
        name: Caller-supplied environment name.

    Raises:
        ValueError: If the name is empty, absolute, or contains path
            separators or parent-directory segments.

    """
    if (
        not name
        or name in {'.', '..'}
        or '/' in name
        or '\\' in name
        or Path(name).name != name
    ):
        raise ValueError(f'invalid environment name: {name!r}')


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
    environment_path: Path | None = None
    requirements_path: Path | None = None


class EnvironmentManager:
    """Manage named Python environments."""

    def __init__(self, runtime_root: Path | None = None) -> None:
        """Initialize an empty environment registry.

        Args:
            runtime_root: Optional filesystem root for managed environments.

        """
        self._records: dict[str, EnvironmentRecord] = {}
        self._runtime_root = runtime_root

    def create(
        self,
        name: str,
        *,
        python_version: str,
        requirements: list[str] | None = None,
    ) -> EnvironmentRecord:
        """Create a new environment record.

        Args:
            name: Environment display name.
            python_version: Target Python version.
            requirements: Optional requirement lines to write.

        Returns:
            The created environment record.

        """
        _validate_env_name(name)
        record = EnvironmentRecord(name=name, python_version=python_version)
        if self._runtime_root is not None:
            environment_path = self._runtime_root / name
            if environment_path.resolve().parent != self._runtime_root.resolve():
                raise ValueError(f'environment escapes runtime root: {name!r}')
            environment_path.mkdir(parents=True, exist_ok=True)
            requirements_path = environment_path / 'requirements.txt'
            if requirements is not None:
                requirements_path.write_text(
                    ''.join(f'{requirement}\n' for requirement in requirements),
                    encoding='utf-8',
                )
                record.requirements_path = requirements_path
            record.environment_path = environment_path
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
        record = self._records.pop(name, None)
        if record is not None and record.environment_path is not None:

            def _on_error(_func: object, path: str, _exc: object) -> None:
                _logger.warning('failed to remove %s during env delete', path)

            shutil.rmtree(record.environment_path, onexc=_on_error)

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
    ) -> Mapping[str, object]:
        """Validate environment metadata and capture probe results."""
        record = self._records[name]
        missing = [key for key, ok in required_imports.items() if not ok]
        record.missing_imports = missing
        record.dependency_count = dependency_count
        record.python_version = python_version
        record.gpu_probe_status = gpu_probe_status
        record.disk_usage_mb = self._measure_disk_usage_mb(record)
        record.validation_status = 'failed' if missing else 'validated'
        return self.summary(name)

    def summary(self, name: str) -> Mapping[str, object]:
        """Return a UI-friendly environment summary."""
        record = self._records[name]
        return {
            'name': record.name,
            'python_version': record.python_version,
            'dependency_count': record.dependency_count,
            'disk_usage_mb': record.disk_usage_mb,
            'validation_status': record.validation_status,
            'missing_imports': list(record.missing_imports),
            'gpu_probe_status': record.gpu_probe_status.value,
        }

    def _measure_disk_usage_mb(self, record: EnvironmentRecord) -> int:
        """Measure managed environment disk usage in whole MiB.

        Args:
            record: Environment record to measure.

        Returns:
            Rounded-up disk usage in MiB.

        """
        if record.environment_path is None or not record.environment_path.exists():
            return 0
        total_bytes = 0
        for path in record.environment_path.rglob('*'):
            if path.is_symlink() or not path.is_file():
                continue
            try:
                total_bytes += path.stat().st_size
            except OSError:
                continue
        if total_bytes == 0:
            return 0
        return (total_bytes + 1024 * 1024 - 1) // (1024 * 1024)
