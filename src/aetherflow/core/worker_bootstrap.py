"""Worker bootstrap helpers for packaged helper processes."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Protocol

from aetherflow.proto import capture_pb2


class WorkerBootstrapClient(Protocol):
    """IPC client methods required by packaged worker bootstrap."""

    def report_heartbeat(
        self,
        *,
        worker_id: str,
        health: str,
        missed_heartbeats: int,
        timestamp_ns: int,
    ) -> capture_pb2.OperationStatus:
        """Report a worker heartbeat to the host.

        Args:
            worker_id: Stable identifier for this worker process.
            health: Self-reported health string (e.g. "RUNNING").
            missed_heartbeats: Number of heartbeat intervals missed.
            timestamp_ns: Monotonic timestamp in nanoseconds.

        Returns:
            Operation status from the host supervisor.

        """

    def forward_worker_log(
        self,
        *,
        worker_id: str,
        level: str,
        message: str,
        timestamp_ns: int,
    ) -> capture_pb2.OperationStatus:
        """Forward a worker log line to the host.

        Args:
            worker_id: Stable identifier for this worker process.
            level: Log level string (e.g. "INFO", "ERROR").
            message: Log message text.
            timestamp_ns: Monotonic timestamp in nanoseconds.

        Returns:
            Operation status confirming log was received.

        """


class WorkerBootstrap:
    """Bootstrap adapter used by packaged worker/helper processes."""

    def __init__(
        self,
        *,
        worker_id: str,
        client: WorkerBootstrapClient,
        clock_ns: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        """Initialize worker bootstrap.

        Args:
            worker_id: Stable worker identifier assigned by the host/package.
            client: CaptureControl IPC client.
            clock_ns: Timestamp provider for deterministic tests.

        """
        self._worker_id = worker_id
        self._client = client
        self._clock_ns = clock_ns

    def report_ready(self) -> capture_pb2.OperationStatus:
        """Report initial worker readiness to the host.

        Returns:
            Host-reported operation status.

        """
        return self._client.report_heartbeat(
            worker_id=self._worker_id,
            health='RUNNING',
            missed_heartbeats=0,
            timestamp_ns=self._clock_ns(),
        )

    def forward_log(self, *, level: str, message: str) -> capture_pb2.OperationStatus:
        """Forward one worker log line to the host.

        Args:
            level: Log level string.
            message: Worker log message.

        Returns:
            Host-reported operation status.

        """
        return self._client.forward_worker_log(
            worker_id=self._worker_id,
            level=level,
            message=message,
            timestamp_ns=self._clock_ns(),
        )
