"""Worker supervision state tracking."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class WorkerHealth(str, Enum):
    """Worker health states."""

    STARTING = "STARTING"
    RUNNING = "RUNNING"
    DEGRADED = "DEGRADED"
    RECOVERING = "RECOVERING"
    FAILED = "FAILED"


@dataclass(slots=True)
class WorkerRecord:
    """Mutable state for a supervised worker."""

    health: WorkerHealth = WorkerHealth.STARTING
    missed_heartbeats: int = 0
    restart_count: int = 0


class WorkerSupervisor:
    """Track worker health and restart budgets."""

    def __init__(self, *, max_restarts: int = 3) -> None:
        """Initialize supervisor state.

        Args:
            max_restarts: Restart attempts allowed before failure.
        """
        self._records: dict[str, WorkerRecord] = {}
        self._max_restarts = max_restarts

    def start(self, worker_id: str) -> None:
        """Start tracking a worker."""
        self._records[worker_id] = WorkerRecord(health=WorkerHealth.RUNNING)

    def record_missed_heartbeat(self, worker_id: str) -> None:
        """Record a missed heartbeat for a worker."""
        record = self._records[worker_id]
        record.missed_heartbeats += 1
        if record.missed_heartbeats >= 3:
            record.restart_count += 1
            record.health = (
                WorkerHealth.FAILED
                if record.restart_count > self._max_restarts
                else WorkerHealth.RECOVERING
            )
        else:
            record.health = WorkerHealth.DEGRADED

    def record_crash(self, worker_id: str) -> None:
        """Record a worker crash."""
        record = self._records[worker_id]
        record.restart_count += 1
        record.health = (
            WorkerHealth.FAILED
            if record.restart_count > self._max_restarts
            else WorkerHealth.RECOVERING
        )

    def status(self, worker_id: str) -> WorkerHealth:
        """Return the current worker health."""
        return self._records[worker_id].health
