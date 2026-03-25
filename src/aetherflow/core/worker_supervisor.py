"""Worker supervision state tracking."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from time import monotonic


class WorkerHealth(StrEnum):
    """Worker health states."""

    STARTING = 'STARTING'
    RUNNING = 'RUNNING'
    DEGRADED = 'DEGRADED'
    RECOVERING = 'RECOVERING'
    FAILED = 'FAILED'
    STOPPED = 'STOPPED'


@dataclass(slots=True)
class WorkerRecord:
    """Mutable state for a supervised worker."""

    health: WorkerHealth = WorkerHealth.STARTING
    missed_heartbeats: int = 0
    restart_count: int = 0
    restart_window_start: float = 0.0
    restart_attempts_in_window: int = 0


@dataclass(frozen=True, slots=True)
class WorkerSnapshot:
    """Immutable snapshot of worker health."""

    worker_id: str
    health: WorkerHealth
    missed_heartbeats: int
    restart_count: int
    restart_attempts_in_window: int


class WorkerSupervisor:
    """Track worker health and restart budgets."""

    def __init__(
        self,
        *,
        max_restarts: int = 3,
        restart_window_s: float = 60.0,
        clock: Callable[[], float] | None = None,
    ) -> None:
        """Initialize supervisor state.

        Args:
            max_restarts: Restart attempts allowed before failure.
            restart_window_s: Time window for restart budget enforcement.
            clock: Monotonic time provider for testing.

        """
        self._records: dict[str, WorkerRecord] = {}
        self._max_restarts = max_restarts
        self._restart_window_s = restart_window_s
        self._clock = clock or monotonic

    def start(self, worker_id: str) -> None:
        """Start tracking a worker."""
        self._records[worker_id] = WorkerRecord(health=WorkerHealth.RUNNING)

    def stop(self, worker_id: str) -> None:
        """Stop tracking and clean up a specific worker."""
        if worker_id in self._records:
            # In a real implementation, this would terminate the process
            self._records[worker_id].health = WorkerHealth.STOPPED
            self._records.pop(worker_id)

    def shutdown(self) -> None:
        """Gracefully stop and clean up all supervised workers."""
        for worker_id in list(self._records.keys()):
            self.stop(worker_id)

    def record_missed_heartbeat(self, worker_id: str) -> None:
        """Record a missed heartbeat for a worker."""
        record = self._records[worker_id]
        record.missed_heartbeats += 1
        if record.missed_heartbeats >= 3:
            record.restart_count += 1
            record.health = self._register_restart(record)
            return
        if record.missed_heartbeats >= 2:
            record.health = WorkerHealth.DEGRADED

    def record_crash(self, worker_id: str) -> None:
        """Record a worker crash."""
        record = self._records[worker_id]
        record.restart_count += 1
        record.health = self._register_restart(record)

    def record_heartbeat(self, worker_id: str) -> None:
        """Record a successful heartbeat and clear degraded state."""
        record = self._records[worker_id]
        record.missed_heartbeats = 0
        if record.health is not WorkerHealth.FAILED:
            record.health = WorkerHealth.RUNNING

    def status(self, worker_id: str) -> WorkerHealth:
        """Return the current worker health."""
        return self._records[worker_id].health

    def snapshot(self) -> list[WorkerSnapshot]:
        """Return immutable snapshots of worker health.

        Returns:
            List of worker health snapshots.

        """
        return [
            WorkerSnapshot(
                worker_id=worker_id,
                health=record.health,
                missed_heartbeats=record.missed_heartbeats,
                restart_count=record.restart_count,
                restart_attempts_in_window=record.restart_attempts_in_window,
            )
            for worker_id, record in sorted(self._records.items())
        ]

    def _register_restart(self, record: WorkerRecord) -> WorkerHealth:
        now = self._clock()
        if now - record.restart_window_start > self._restart_window_s:
            record.restart_window_start = now
            record.restart_attempts_in_window = 0
        record.restart_attempts_in_window += 1
        if record.restart_attempts_in_window > self._max_restarts:
            return WorkerHealth.FAILED
        return WorkerHealth.RECOVERING
