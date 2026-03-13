"""Environment panel model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast

from aetherflow.core.env_manager import EnvironmentManager, GpuProbeStatus


@dataclass(frozen=True, slots=True)
class EnvironmentSummary:
    """Environment summary for UI display."""

    name: str
    python_version: str
    dependency_count: int
    validation_status: str
    missing_imports: list[str] = field(default_factory=list)
    gpu_probe_status: GpuProbeStatus = GpuProbeStatus.NOT_RUN


@dataclass(frozen=True, slots=True)
class EnvironmentPanelModel:
    """Environment panel state."""

    environments: list[EnvironmentSummary]
    failed_count: int
    pending_count: int

    @classmethod
    def from_manager(cls, manager: EnvironmentManager) -> EnvironmentPanelModel:
        """Build an environment panel from the manager state.

        Args:
            manager: Environment manager containing environment records.

        Returns:
            Environment panel model.

        """
        summaries: list[EnvironmentSummary] = []
        for name in sorted(manager.list_names()):
            summary = manager.summary(name)
            summaries.append(
                EnvironmentSummary(
                    name=cast(str, summary['name']),
                    python_version=cast(str, summary['python_version']),
                    dependency_count=cast(int, summary['dependency_count']),
                    validation_status=cast(str, summary['validation_status']),
                    missing_imports=list(cast(list[str], summary['missing_imports'])),
                    gpu_probe_status=GpuProbeStatus(
                        cast(str, summary['gpu_probe_status'])
                    ),
                )
            )
        failed_count = sum(
            1 for summary in summaries if summary.validation_status == 'failed'
        )
        pending_count = sum(
            1 for summary in summaries if summary.validation_status == 'pending'
        )
        return cls(
            environments=summaries,
            failed_count=failed_count,
            pending_count=pending_count,
        )
