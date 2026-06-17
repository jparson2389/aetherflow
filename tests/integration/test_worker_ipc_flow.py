from concurrent import futures

import grpc

from aetherflow.core.ipc import CaptureControlClient, capture_pb2_grpc
from aetherflow.core.worker_supervisor import WorkerHealth, WorkerStateView
from aetherflow.proto import capture_pb2


class WorkerStateCaptureControl(capture_pb2_grpc.CaptureControlServicer):
    """In-process CaptureControl service backed by host-reported state view."""

    def __init__(self, state_view: WorkerStateView) -> None:
        """Initialize the service."""
        self._state_view = state_view
        self.logs: list[capture_pb2.WorkerLog] = []

    def ReportHeartbeat(
        self,
        request: capture_pb2.WorkerHeartbeat,
        _context: grpc.ServicerContext,
    ) -> capture_pb2.OperationStatus:
        """Apply host-style heartbeat state through the gRPC endpoint."""
        self._state_view.apply_heartbeat(
            request.worker_id,
            health=WorkerHealth(request.health),
            missed_heartbeats=request.missed_heartbeats,
        )
        return capture_pb2.OperationStatus(
            ok=True,
            runtime_state=request.health,
            message='heartbeat recorded',
        )

    def ForwardWorkerLog(
        self,
        request: capture_pb2.WorkerLog,
        _context: grpc.ServicerContext,
    ) -> capture_pb2.OperationStatus:
        """Record a worker log through the gRPC endpoint."""
        self.logs.append(request)
        return capture_pb2.OperationStatus(
            ok=True,
            runtime_state='RUNNING',
            message='log recorded',
        )


def test_worker_heartbeat_and_logs_flow_through_capture_control_ipc() -> None:
    """Worker heartbeat and logs move through gRPC CaptureControl."""
    state_view = WorkerStateView()
    state_view.register('vision-worker')
    service = WorkerStateCaptureControl(state_view)
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
    capture_pb2_grpc.add_CaptureControlServicer_to_server(service, server)
    port = server.add_insecure_port('127.0.0.1:0')
    server.start()

    try:
        client = CaptureControlClient.connect(f'127.0.0.1:{port}')

        heartbeat_status = client.report_heartbeat(
            worker_id='vision-worker',
            health='RUNNING',
            missed_heartbeats=0,
            timestamp_ns=123456789,
        )
        log_status = client.forward_worker_log(
            worker_id='vision-worker',
            level='INFO',
            message='frame ready',
            timestamp_ns=123456790,
        )

        assert heartbeat_status.ok is True
        assert log_status.ok is True
        assert state_view.status('vision-worker') is WorkerHealth.RUNNING
        assert len(service.logs) == 1
        assert service.logs[0].message == 'frame ready'
    finally:
        server.stop(grace=None)
