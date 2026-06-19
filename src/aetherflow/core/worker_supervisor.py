"""Host-reported worker state view.

The host C++ supervisor (``WorkerSupervisorImpl`` in ``host/supervisor.cpp``)
is the sole authority for all supervision decisions. This module provides
``WorkerStateView``, a read-only mirror that applies state reports received
from the host via the gRPC control plane and surfaces them to shell consumers.

``WorkerStateView`` must never make restart or health-transition decisions.
All transition logic (missed-heartbeat escalation, restart-budget enforcement,
failure isolation) lives in the native host.

New code must use ``WorkerStateView`` directly.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum

_logger = logging.getLogger(__name__)


class WorkerHealth(StrEnum):
    """Worker health states as reported by the host supervisor."""

    STARTING = 'STARTING'
    RUNNING = 'RUNNING'
    DEGRADED = 'DEGRADED'
    RECOVERING = 'RECOVERING'
    FAILED = 'FAILED'


@dataclass(slots=True)
class WorkerRecord:
    """Mutable state for a supervised worker unit."""

    health: WorkerHealth = WorkerHealth.STARTING
    missed_heartbeats: int = 0
    restart_count: int = 0
    restart_attempts_in_window: int = 0


@dataclass(frozen=True, slots=True)
class WorkerSnapshot:
    """Immutable snapshot of worker health for a single unit."""

    worker_id: str
    health: WorkerHealth
    missed_heartbeats: int
    restart_count: int
    restart_attempts_in_window: int


class WorkerStateView:
    """Read-only mirror of host-reported worker state.

    The host supervisor is the single authority for all supervision decisions.
    This class stores the state the host has reported and exposes it to shell
    consumers. It must not compute state transitions independently.
    """

    def __init__(self) -> None:
        """Initialize an empty worker state view."""
        self._records: dict[str, WorkerRecord] = {}

    def register(self, worker_id: str) -> None:
        """Register a worker slot to receive host state reports.

        Args:
            worker_id: Stable identifier for the worker unit.

        """
        self._records[worker_id] = WorkerRecord()

    def _record_for(self, worker_id: str) -> WorkerRecord:
        """Return the record for a worker, auto-registering if the host reports a new one.

        The host supervisor is the authority for which workers exist; a report
        for an unregistered id means the shell view simply has not seen it yet,
        so it is registered rather than allowed to crash the shell.

        Args:
            worker_id: Stable identifier for the worker unit.

        Returns:
            The existing or newly created worker record.

        """
        record = self._records.get(worker_id)
        if record is None:
            _logger.warning(
                'host reported state for unregistered worker %s; auto-registering',
                worker_id,
            )
            record = WorkerRecord()
            self._records[worker_id] = record
        return record

    def apply_heartbeat(
        self,
        worker_id: str,
        *,
        health: WorkerHealth,
        missed_heartbeats: int,
    ) -> None:
        """Apply a heartbeat report received from the host supervisor.

        Args:
            worker_id: Stable identifier for the worker unit.
            health: Health state as determined by the host supervisor.
            missed_heartbeats: Missed-heartbeat count reported by the host.

        """
        record = self._record_for(worker_id)
        record.health = health
        record.missed_heartbeats = missed_heartbeats

    def apply_crash_result(
        self,
        worker_id: str,
        *,
        health: WorkerHealth,
        restart_count: int,
        restart_attempts_in_window: int,
    ) -> None:
        """Apply a crash or restart-budget result reported by the host supervisor.

        Args:
            worker_id: Stable identifier for the worker unit.
            health: Resulting health as decided by the host.
            restart_count: Total restart count reported by the host.
            restart_attempts_in_window: Restart attempts within the current window.

        """
        record = self._record_for(worker_id)
        record.health = health
        record.restart_count = restart_count
        record.restart_attempts_in_window = restart_attempts_in_window

    def status(self, worker_id: str) -> WorkerHealth:
        """Return the last health state reported by the host for this worker.

        Args:
            worker_id: Stable identifier for the worker unit.

        Returns:
            Most recent WorkerHealth value applied from a host report.

        """
        return self._records[worker_id].health

    def snapshot(self) -> list[WorkerSnapshot]:
        """Return immutable snapshots of all registered workers.

        Returns:
            Worker snapshots sorted by worker identifier for deterministic output.

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
