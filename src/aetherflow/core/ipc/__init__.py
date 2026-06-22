"""Python client helpers for the frozen CaptureControl IPC surface."""

from __future__ import annotations

import importlib
import sys
from collections.abc import Sequence
from typing import Protocol

import grpc

from aetherflow.proto import capture_pb2

sys.modules.setdefault('capture_pb2', capture_pb2)
capture_pb2_grpc = importlib.import_module('aetherflow.proto.capture_pb2_grpc')

DEFAULT_UNARY_TIMEOUT_S = 0.750
_RETRYABLE_STATUS_CODES = {
    grpc.StatusCode.DEADLINE_EXCEEDED,
    grpc.StatusCode.UNAVAILABLE,
}

# Mirrors the server-side IsLoopbackAddress check in
# host/capture_control_server.cpp so client and server enforce the same policy.
_LOOPBACK_PREFIXES = ('127.0.0.1:', '[::1]:', 'localhost:', 'unix:')


def _is_loopback_target(target: str) -> bool:
    """Return whether a gRPC target addresses the local loopback interface.

    Args:
        target: gRPC target string such as ``127.0.0.1:50051``.

    Returns:
        True if the target is a loopback/localhost/unix-socket address.

    """
    return target.startswith(_LOOPBACK_PREFIXES)


class CaptureControlStubProtocol(Protocol):
    """Subset of the generated CaptureControl stub used by the client."""

    def StartCapture(
        self,
        request: capture_pb2.CaptureStartRequest,
        *,
        timeout: float | None = None,
    ) -> capture_pb2.OperationStatus:
        """Start capture through the generated gRPC method.

        Args:
            request: Capture start parameters including plugin id and device.
            timeout: Unary RPC deadline in seconds.

        Returns:
            Operation status with runtime state and retry budget.

        """

    def StopCapture(
        self,
        request: capture_pb2.CaptureStopRequest,
        *,
        timeout: float | None = None,
    ) -> capture_pb2.OperationStatus:
        """Stop capture through the generated gRPC method.

        Args:
            request: Capture stop parameters including plugin id and reason.
            timeout: Unary RPC deadline in seconds.

        Returns:
            Operation status with runtime state and retry budget.

        """

    def ReportHeartbeat(
        self,
        request: capture_pb2.WorkerHeartbeat,
        *,
        timeout: float | None = None,
    ) -> capture_pb2.OperationStatus:
        """Report worker heartbeat through the generated gRPC method.

        Args:
            request: Heartbeat payload including worker id and missed count.
            timeout: Unary RPC deadline in seconds.

        Returns:
            Operation status reflecting the resulting supervisor state.

        """

    def ForwardWorkerLog(
        self,
        request: capture_pb2.WorkerLog,
        *,
        timeout: float | None = None,
    ) -> capture_pb2.OperationStatus:
        """Forward worker log through the generated gRPC method.

        Args:
            request: Log payload including worker id, level, and message.
            timeout: Unary RPC deadline in seconds.

        Returns:
            Operation status confirming log was received.

        """

    def ReportPluginLoadResult(
        self,
        request: capture_pb2.PluginLoadResult,
        *,
        timeout: float | None = None,
    ) -> capture_pb2.OperationStatus:
        """Report plugin load result through the generated gRPC method.

        Args:
            request: Load result including plugin id and success flag.
            timeout: Unary RPC deadline in seconds.

        Returns:
            Operation status reflecting the resulting supervisor state.

        """

    def ExportDiagnostics(
        self,
        request: capture_pb2.DiagnosticsExportRequest,
        *,
        timeout: float | None = None,
    ) -> capture_pb2.DiagnosticsExportResponse:
        """Export diagnostics through the generated gRPC method.

        Args:
            request: Diagnostics export parameters.
            timeout: Unary RPC deadline in seconds.

        Returns:
            Diagnostics export response with current endpoint state.

        """


class CaptureControlClient:
    """Client wrapper for host-owned CaptureControl operations."""

    def __init__(self, stub: CaptureControlStubProtocol) -> None:
        """Initialize the client with a generated or test stub.

        Args:
            stub: Object exposing the generated CaptureControl RPC callables.

        """
        self._stub = stub

    def _call_operation(
        self,
        method_name: str,
        request: object,
        *,
        timeout_s: float = DEFAULT_UNARY_TIMEOUT_S,
        retry_once: bool = False,
    ) -> capture_pb2.OperationStatus:
        """Call one OperationStatus RPC with the frozen timeout policy.

        Args:
            method_name: Generated stub method name.
            request: Protobuf request object.
            timeout_s: Unary RPC deadline in seconds.
            retry_once: Whether to retry once for transient transport errors.

        Returns:
            Operation status returned by the host.

        Raises:
            grpc.RpcError: If transport fails and retry policy is exhausted.

        """
        method = getattr(self._stub, method_name)
        try:
            return method(request, timeout=timeout_s)
        except grpc.RpcError as exc:
            if not retry_once or exc.code() not in _RETRYABLE_STATUS_CODES:
                raise
            return method(request, timeout=timeout_s)

    def _call_diagnostics(
        self,
        request: capture_pb2.DiagnosticsExportRequest,
        *,
        timeout_s: float = DEFAULT_UNARY_TIMEOUT_S,
    ) -> capture_pb2.DiagnosticsExportResponse:
        """Call ExportDiagnostics with the frozen timeout policy.

        Args:
            request: Diagnostics request.
            timeout_s: Unary RPC deadline in seconds.

        Returns:
            Diagnostics export response.

        """
        return self._stub.ExportDiagnostics(request, timeout=timeout_s)

    @classmethod
    def connect(
        cls, target: str, *, allow_remote: bool = False
    ) -> CaptureControlClient:
        """Create a client connected to a host CaptureControl endpoint.

        The control plane uses insecure (plaintext) gRPC, so by default the
        client refuses non-loopback targets — symmetric with the server, which
        rejects non-loopback binds unless ``--allow-remote`` is passed.

        Args:
            target: gRPC target such as ``127.0.0.1:50051``.
            allow_remote: Permit a non-loopback target. Off by default.

        Returns:
            CaptureControl client bound to the generated stub.

        Raises:
            ValueError: If ``target`` is non-loopback and ``allow_remote`` is
                False.

        """
        if not allow_remote and not _is_loopback_target(target):
            raise ValueError(
                f'refusing non-loopback CaptureControl target {target!r} '
                'over insecure credentials; pass allow_remote=True to override'
            )
        channel = grpc.insecure_channel(target)
        return cls(capture_pb2_grpc.CaptureControlStub(channel))

    def start_capture(
        self,
        *,
        capture_plugin_id: str,
        device_id: str,
        width: int,
        height: int,
        target_fps: int,
        pixel_format: str,
        stride_bytes: int,
        timeout_ms: int,
    ) -> capture_pb2.OperationStatus:
        """Request capture start through the frozen control-plane RPC.

        Args:
            capture_plugin_id: Capture plugin identifier.
            device_id: Capture device identifier.
            width: Requested frame width in pixels.
            height: Requested frame height in pixels.
            target_fps: Requested capture rate.
            pixel_format: Requested pixel format.
            stride_bytes: Expected frame stride.
            timeout_ms: Host-side start timeout in milliseconds.

        Returns:
            Host-reported operation status.

        """
        request = capture_pb2.CaptureStartRequest(
            capture_plugin_id=capture_plugin_id,
            device_id=device_id,
            mode=capture_pb2.CaptureMode(
                width=width,
                height=height,
                target_fps=target_fps,
                pixel_format=pixel_format,
                stride_bytes=stride_bytes,
            ),
            timeout_ms=timeout_ms,
        )
        timeout_s = DEFAULT_UNARY_TIMEOUT_S
        if timeout_ms > 0:
            timeout_s = min(DEFAULT_UNARY_TIMEOUT_S, timeout_ms / 1000)
        return self._call_operation(
            'StartCapture',
            request,
            timeout_s=timeout_s,
            retry_once=True,
        )

    def stop_capture(
        self,
        *,
        capture_plugin_id: str,
        device_id: str,
        reason: str,
    ) -> capture_pb2.OperationStatus:
        """Request capture stop through the frozen control-plane RPC.

        Args:
            capture_plugin_id: Capture plugin identifier.
            device_id: Capture device identifier.
            reason: Human-readable stop reason for host diagnostics.

        Returns:
            Host-reported operation status.

        """
        request = capture_pb2.CaptureStopRequest(
            capture_plugin_id=capture_plugin_id,
            device_id=device_id,
            reason=reason,
        )
        return self._call_operation('StopCapture', request, retry_once=True)

    def report_heartbeat(
        self,
        *,
        worker_id: str,
        health: str,
        missed_heartbeats: int,
        timestamp_ns: int,
    ) -> capture_pb2.OperationStatus:
        """Report worker heartbeat through the frozen control-plane RPC.

        Args:
            worker_id: Stable worker identifier.
            health: Host-compatible health string.
            missed_heartbeats: Missed-heartbeat count observed by the reporter.
            timestamp_ns: Monotonic or host-correlated timestamp in nanoseconds.

        Returns:
            Host-reported operation status.

        """
        request = capture_pb2.WorkerHeartbeat(
            worker_id=worker_id,
            health=health,
            missed_heartbeats=missed_heartbeats,
            timestamp_ns=timestamp_ns,
        )
        return self._call_operation('ReportHeartbeat', request)

    def forward_worker_log(
        self,
        *,
        worker_id: str,
        level: str,
        message: str,
        timestamp_ns: int,
    ) -> capture_pb2.OperationStatus:
        """Forward a worker log line through the frozen control-plane RPC.

        Args:
            worker_id: Stable worker identifier.
            level: Log level string.
            message: Worker log message.
            timestamp_ns: Log timestamp in nanoseconds.

        Returns:
            Host-reported operation status.

        """
        request = capture_pb2.WorkerLog(
            worker_id=worker_id,
            level=level,
            message=message,
            timestamp_ns=timestamp_ns,
        )
        return self._call_operation('ForwardWorkerLog', request)

    def report_plugin_load_result(
        self,
        *,
        plugin_id: str,
        loaded: bool,
        runtime_state: str,
        error_code: str = '',
        error_message: str = '',
    ) -> capture_pb2.OperationStatus:
        """Report plugin load outcome through the frozen control-plane RPC.

        Args:
            plugin_id: Stable plugin identifier.
            loaded: Whether the plugin loaded successfully.
            runtime_state: Host-compatible runtime state.
            error_code: Optional load failure code.
            error_message: Optional load failure detail.

        Returns:
            Host-reported operation status.

        """
        request = capture_pb2.PluginLoadResult(
            plugin_id=plugin_id,
            loaded=loaded,
            runtime_state=runtime_state,
            error_code=error_code,
            error_message=error_message,
        )
        return self._call_operation(
            'ReportPluginLoadResult',
            request,
            retry_once=True,
        )

    def export_diagnostics(
        self,
        *,
        include_sections: Sequence[str],
        include_recent_logs: bool,
    ) -> capture_pb2.DiagnosticsExportResponse:
        """Request diagnostics export through the frozen control-plane RPC.

        Args:
            include_sections: Diagnostics section names to include.
            include_recent_logs: Whether recent logs should be included.

        Returns:
            Host-reported diagnostics artifact response.

        """
        request = capture_pb2.DiagnosticsExportRequest(
            include_sections=list(include_sections),
            include_recent_logs=include_recent_logs,
        )
        return self._call_diagnostics(request)


__all__ = ['DEFAULT_UNARY_TIMEOUT_S', 'CaptureControlClient']
