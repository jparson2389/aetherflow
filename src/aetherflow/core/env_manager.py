"""Environment management state."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class EnvironmentRecord:
    """Environment metadata shown in the UI."""

    name: str
    python_version: str
    dependency_count: int = 0
    disk_usage_mb: int = 0
    validation_status: str = "pending"


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

    def summary(self, name: str) -> dict[str, str | int]:
        """Return a UI-friendly environment summary."""
        record = self._records[name]
        return {
            "name": record.name,
            "python_version": record.python_version,
            "validation_status": record.validation_status,
        }
