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


class CaptureControlStubProtocol(Protocol):
    """Subset of the generated CaptureControl stub used by the client."""

    def StartCapture(
        self,
        request: capture_pb2.CaptureStartRequest,
    ) -> capture_pb2.OperationStatus:
        """Start capture through the generated gRPC method."""

    def StopCapture(
        self,
        request: capture_pb2.CaptureStopRequest,
    ) -> capture_pb2.OperationStatus:
        """Stop capture through the generated gRPC method."""

    def ReportHeartbeat(
        self,
        request: capture_pb2.WorkerHeartbeat,
    ) -> capture_pb2.OperationStatus:
        """Report worker heartbeat through the generated gRPC method."""

    def ForwardWorkerLog(
        self,
        request: capture_pb2.WorkerLog,
    ) -> capture_pb2.OperationStatus:
        """Forward worker log through the generated gRPC method."""

    def ReportPluginLoadResult(
        self,
        request: capture_pb2.PluginLoadResult,
    ) -> capture_pb2.OperationStatus:
        """Report plugin load result through the generated gRPC method."""

    def ExportDiagnostics(
        self,
        request: capture_pb2.DiagnosticsExportRequest,
    ) -> capture_pb2.DiagnosticsExportResponse:
        """Export diagnostics through the generated gRPC method."""


class CaptureControlClient:
    """Client wrapper for host-owned CaptureControl operations."""

    def __init__(self, stub: CaptureControlStubProtocol) -> None:
        """Initialize the client with a generated or test stub.

        Args:
            stub: Object exposing the generated CaptureControl RPC callables.

        """
        self._stub = stub

    @classmethod
    def connect(cls, target: str) -> CaptureControlClient:
        """Create a client connected to a host CaptureControl endpoint.

        Args:
            target: gRPC target such as ``127.0.0.1:50051``.

        Returns:
            CaptureControl client bound to the generated stub.

        """
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
        return self._stub.StartCapture(request)

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
        return self._stub.StopCapture(request)

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
        return self._stub.ReportHeartbeat(request)

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
        return self._stub.ForwardWorkerLog(request)

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
        return self._stub.ReportPluginLoadResult(request)

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
        return self._stub.ExportDiagnostics(request)


__all__ = ['CaptureControlClient']
