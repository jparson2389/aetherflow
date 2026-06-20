import grpc

from aetherflow.core.ipc import DEFAULT_UNARY_TIMEOUT_S, CaptureControlClient
from aetherflow.proto import capture_pb2


class FakeRpcError(grpc.RpcError):
    """RPC error with a deterministic status code for retry tests."""

    def __init__(self, status_code: grpc.StatusCode) -> None:
        """Initialize the fake with the gRPC status code to expose."""
        self._status_code = status_code

    def code(self) -> grpc.StatusCode:
        """Return the configured status code."""
        return self._status_code


class FakeCaptureControlStub:
    """CaptureControl stub that records requests for unit tests."""

    def __init__(self) -> None:
        """Initialize the fake with no captured requests."""
        self.start_capture_request: capture_pb2.CaptureStartRequest | None = None
        self.stop_capture_request: capture_pb2.CaptureStopRequest | None = None
        self.heartbeat_request: capture_pb2.WorkerHeartbeat | None = None
        self.worker_log_request: capture_pb2.WorkerLog | None = None
        self.plugin_load_result: capture_pb2.PluginLoadResult | None = None
        self.diagnostics_request: capture_pb2.DiagnosticsExportRequest | None = None
        self.timeouts: list[float | None] = []
        self.start_failures_remaining = 0

    def StartCapture(
        self,
        request: capture_pb2.CaptureStartRequest,
        *,
        timeout: float | None = None,
    ) -> capture_pb2.OperationStatus:
        """Record a start request and return a successful status."""
        self.start_capture_request = request
        self.timeouts.append(timeout)
        if self.start_failures_remaining > 0:
            self.start_failures_remaining -= 1
            raise FakeRpcError(grpc.StatusCode.UNAVAILABLE)
        return capture_pb2.OperationStatus(
            ok=True,
            runtime_state='RUNNING',
            message='started',
            retry_budget_remaining=3,
        )

    def StopCapture(
        self,
        request: capture_pb2.CaptureStopRequest,
        *,
        timeout: float | None = None,
    ) -> capture_pb2.OperationStatus:
        """Record a stop request and return a successful status."""
        self.stop_capture_request = request
        self.timeouts.append(timeout)
        return capture_pb2.OperationStatus(
            ok=True,
            runtime_state='FAILED',
            message='stopped',
            retry_budget_remaining=3,
        )

    def ReportHeartbeat(
        self,
        request: capture_pb2.WorkerHeartbeat,
        *,
        timeout: float | None = None,
    ) -> capture_pb2.OperationStatus:
        """Record a heartbeat request and return a successful status."""
        self.heartbeat_request = request
        self.timeouts.append(timeout)
        return capture_pb2.OperationStatus(
            ok=True,
            runtime_state='RUNNING',
            message='heartbeat',
            retry_budget_remaining=3,
        )

    def ForwardWorkerLog(
        self,
        request: capture_pb2.WorkerLog,
        *,
        timeout: float | None = None,
    ) -> capture_pb2.OperationStatus:
        """Record a worker log request and return a successful status."""
        self.worker_log_request = request
        self.timeouts.append(timeout)
        return capture_pb2.OperationStatus(
            ok=True,
            runtime_state='RUNNING',
            message='logged',
            retry_budget_remaining=3,
        )

    def ReportPluginLoadResult(
        self,
        request: capture_pb2.PluginLoadResult,
        *,
        timeout: float | None = None,
    ) -> capture_pb2.OperationStatus:
        """Record a plugin load result and return a successful status."""
        self.plugin_load_result = request
        self.timeouts.append(timeout)
        return capture_pb2.OperationStatus(
            ok=True,
            runtime_state='RUNNING',
            message='plugin result',
            retry_budget_remaining=3,
        )

    def ExportDiagnostics(
        self,
        request: capture_pb2.DiagnosticsExportRequest,
        *,
        timeout: float | None = None,
    ) -> capture_pb2.DiagnosticsExportResponse:
        """Record a diagnostics request and return an artifact response."""
        self.diagnostics_request = request
        self.timeouts.append(timeout)
        return capture_pb2.DiagnosticsExportResponse(
            artifact_path='diagnostics.zip',
            summary='exported',
        )


def test_start_capture_sends_frozen_proto_request() -> None:
    """Start capture sends the frozen CaptureStartRequest shape."""
    stub = FakeCaptureControlStub()
    client = CaptureControlClient(stub)

    status = client.start_capture(
        capture_plugin_id='opencv-capture',
        device_id='camera-0',
        width=1920,
        height=1080,
        target_fps=120,
        pixel_format='BGR24',
        stride_bytes=5760,
        timeout_ms=500,
    )

    assert status.ok is True
    assert stub.start_capture_request is not None
    assert stub.start_capture_request.capture_plugin_id == 'opencv-capture'
    assert stub.start_capture_request.device_id == 'camera-0'
    assert stub.start_capture_request.mode.width == 1920
    assert stub.start_capture_request.mode.target_fps == 120
    assert stub.start_capture_request.timeout_ms == 500
    assert stub.timeouts == [0.5]


def test_start_capture_retries_once_on_transient_transport_error() -> None:
    """Start capture retries once on transient transport failures."""
    stub = FakeCaptureControlStub()
    stub.start_failures_remaining = 1
    client = CaptureControlClient(stub)

    status = client.start_capture(
        capture_plugin_id='opencv-capture',
        device_id='camera-0',
        width=1920,
        height=1080,
        target_fps=120,
        pixel_format='BGR24',
        stride_bytes=5760,
        timeout_ms=1000,
    )

    assert status.ok is True
    assert stub.timeouts == [DEFAULT_UNARY_TIMEOUT_S, DEFAULT_UNARY_TIMEOUT_S]


def test_stop_capture_sends_frozen_proto_request() -> None:
    """Stop capture sends the frozen CaptureStopRequest shape."""
    stub = FakeCaptureControlStub()
    client = CaptureControlClient(stub)

    status = client.stop_capture(
        capture_plugin_id='opencv-capture',
        device_id='camera-0',
        reason='user-request',
    )

    assert status.ok is True
    assert stub.stop_capture_request is not None
    assert stub.stop_capture_request.capture_plugin_id == 'opencv-capture'
    assert stub.stop_capture_request.device_id == 'camera-0'
    assert stub.stop_capture_request.reason == 'user-request'
    assert stub.timeouts == [DEFAULT_UNARY_TIMEOUT_S]


def test_report_heartbeat_sends_frozen_proto_request() -> None:
    """Worker heartbeat sends the frozen WorkerHeartbeat shape."""
    stub = FakeCaptureControlStub()
    client = CaptureControlClient(stub)

    status = client.report_heartbeat(
        worker_id='vision-worker',
        health='RUNNING',
        missed_heartbeats=0,
        timestamp_ns=123456789,
    )

    assert status.ok is True
    assert stub.heartbeat_request is not None
    assert stub.heartbeat_request.worker_id == 'vision-worker'
    assert stub.heartbeat_request.health == 'RUNNING'
    assert stub.heartbeat_request.missed_heartbeats == 0
    assert stub.heartbeat_request.timestamp_ns == 123456789
    assert stub.timeouts == [DEFAULT_UNARY_TIMEOUT_S]


def test_forward_worker_log_sends_frozen_proto_request() -> None:
    """Worker log forwarding sends the frozen WorkerLog shape."""
    stub = FakeCaptureControlStub()
    client = CaptureControlClient(stub)

    status = client.forward_worker_log(
        worker_id='vision-worker',
        level='INFO',
        message='frame ready',
        timestamp_ns=987654321,
    )

    assert status.ok is True
    assert stub.worker_log_request is not None
    assert stub.worker_log_request.worker_id == 'vision-worker'
    assert stub.worker_log_request.level == 'INFO'
    assert stub.worker_log_request.message == 'frame ready'
    assert stub.worker_log_request.timestamp_ns == 987654321
    assert stub.timeouts == [DEFAULT_UNARY_TIMEOUT_S]


def test_report_plugin_load_result_sends_frozen_proto_request() -> None:
    """Plugin load result sends the frozen PluginLoadResult shape."""
    stub = FakeCaptureControlStub()
    client = CaptureControlClient(stub)

    status = client.report_plugin_load_result(
        plugin_id='capture-plugin',
        loaded=False,
        runtime_state='FAILED',
        error_code='signature-denied',
        error_message='signature failed',
    )

    assert status.ok is True
    assert stub.plugin_load_result is not None
    assert stub.plugin_load_result.plugin_id == 'capture-plugin'
    assert stub.plugin_load_result.loaded is False
    assert stub.plugin_load_result.runtime_state == 'FAILED'
    assert stub.plugin_load_result.error_code == 'signature-denied'
    assert stub.plugin_load_result.error_message == 'signature failed'
    assert stub.timeouts == [DEFAULT_UNARY_TIMEOUT_S]


def test_export_diagnostics_sends_frozen_proto_request() -> None:
    """Diagnostics export sends the frozen DiagnosticsExportRequest shape."""
    stub = FakeCaptureControlStub()
    client = CaptureControlClient(stub)

    response = client.export_diagnostics(
        include_sections=['workers', 'plugins'],
        include_recent_logs=True,
    )

    assert response.artifact_path == 'diagnostics.zip'
    assert stub.diagnostics_request is not None
    assert list(stub.diagnostics_request.include_sections) == [
        'workers',
        'plugins',
    ]
    assert stub.diagnostics_request.include_recent_logs is True
    assert stub.timeouts == [DEFAULT_UNARY_TIMEOUT_S]
