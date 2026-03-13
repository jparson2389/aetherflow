"""Worker health panel model."""

from __future__ import annotations

from dataclasses import dataclass

from aetherflow.core.worker_supervisor import (
    WorkerHealth,
    WorkerSnapshot,
    WorkerSupervisor,
)


@dataclass(frozen=True, slots=True)
class WorkerHealthPanelModel:
    """UI model for worker health."""

    worker_id: str
    health: WorkerHealth
    missed_heartbeats: int = 0
    restart_count: int = 0
    restart_attempts_in_window: int = 0

    def to_payload(self) -> dict[str, object]:
        """Return a JSON-serializable health payload."""
        return {
            'worker_id': self.worker_id,
            'health': self.health.value,
            'missed_heartbeats': self.missed_heartbeats,
            'restart_count': self.restart_count,
            'restart_attempts_in_window': self.restart_attempts_in_window,
        }

    @classmethod
    def from_snapshot(cls, snapshot: WorkerSnapshot) -> WorkerHealthPanelModel:
        """Build a panel model from a worker snapshot.

        Args:
            snapshot: Worker snapshot data.

        Returns:
            Worker health panel model.

        """
        return cls(
            worker_id=snapshot.worker_id,
            health=snapshot.health,
            missed_heartbeats=snapshot.missed_heartbeats,
            restart_count=snapshot.restart_count,
            restart_attempts_in_window=snapshot.restart_attempts_in_window,
        )

    @classmethod
    def list_from_supervisor(
        cls,
        supervisor: WorkerSupervisor,
    ) -> list[WorkerHealthPanelModel]:
        """Build panel models from supervisor state.

        Args:
            supervisor: Worker supervisor to snapshot.

        Returns:
            List of worker health panel models.

        """
        return [cls.from_snapshot(snapshot) for snapshot in supervisor.snapshot()]
