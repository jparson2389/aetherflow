from aetherflow.core.worker_bootstrap import WorkerBootstrap
from aetherflow.proto import capture_pb2


class RecordingCaptureClient:
    """Capture client fake that records worker bootstrap calls."""

    def __init__(self) -> None:
        """Initialize empty call records."""
        self.heartbeats: list[dict[str, object]] = []
        self.logs: list[dict[str, object]] = []

    def report_heartbeat(
        self,
        *,
        worker_id: str,
        health: str,
        missed_heartbeats: int,
        timestamp_ns: int,
    ) -> capture_pb2.OperationStatus:
        """Record heartbeat arguments."""
        self.heartbeats.append(
            {
                'worker_id': worker_id,
                'health': health,
                'missed_heartbeats': missed_heartbeats,
                'timestamp_ns': timestamp_ns,
            }
        )
        return capture_pb2.OperationStatus(ok=True, runtime_state='RUNNING')

    def forward_worker_log(
        self,
        *,
        worker_id: str,
        level: str,
        message: str,
        timestamp_ns: int,
    ) -> capture_pb2.OperationStatus:
        """Record worker log arguments."""
        self.logs.append(
            {
                'worker_id': worker_id,
                'level': level,
                'message': message,
                'timestamp_ns': timestamp_ns,
            }
        )
        return capture_pb2.OperationStatus(ok=True, runtime_state='RUNNING')


def test_worker_bootstrap_reports_ready_heartbeat() -> None:
    """Worker bootstrap reports an initial RUNNING heartbeat through IPC."""
    client = RecordingCaptureClient()
    bootstrap = WorkerBootstrap(
        worker_id='vision-worker',
        client=client,
        clock_ns=lambda: 123456789,
    )

    status = bootstrap.report_ready()

    assert status.ok is True
    assert client.heartbeats == [
        {
            'worker_id': 'vision-worker',
            'health': 'RUNNING',
            'missed_heartbeats': 0,
            'timestamp_ns': 123456789,
        }
    ]


def test_worker_bootstrap_forwards_log_line() -> None:
    """Worker bootstrap forwards helper logs through IPC."""
    client = RecordingCaptureClient()
    bootstrap = WorkerBootstrap(
        worker_id='vision-worker',
        client=client,
        clock_ns=lambda: 987654321,
    )

    status = bootstrap.forward_log(level='INFO', message='frame ready')

    assert status.ok is True
    assert client.logs == [
        {
            'worker_id': 'vision-worker',
            'level': 'INFO',
            'message': 'frame ready',
            'timestamp_ns': 987654321,
        }
    ]
