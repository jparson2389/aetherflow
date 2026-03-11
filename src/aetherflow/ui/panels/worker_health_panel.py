"""Worker health panel model."""

from __future__ import annotations

from dataclasses import dataclass

from aetherflow.core.worker_supervisor import WorkerHealth


@dataclass(frozen=True, slots=True)
class WorkerHealthPanelModel:
    """UI model for worker health."""

    worker_id: str
    health: WorkerHealth

    def to_payload(self) -> dict[str, str]:
        """Return a JSON-serializable health payload."""
        return {'worker_id': self.worker_id, 'health': self.health.value}
