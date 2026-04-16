# Capture Control Plane

`proto/capture.proto` defines the minimum frozen control-plane contract for:

- capture start and stop
- worker heartbeats
- worker log forwarding
- plugin load result reporting
- diagnostics export requests
- diagnostics export responses

## Frozen Surface

The Phase 0 wire surface is normative for implementations. Automated checks in
`tests/contracts/test_execution_contracts.py` assert a curated subset of
`proto/capture.proto` text (see `test_capture_proto_defines_required_control_plane_messages`);
they do not exhaustively fail on every missing message type or RPC name.

- `CaptureMode`: `width`, `height`, `target_fps`, `pixel_format`,
  `stride_bytes`
- `CaptureStartRequest`: `capture_plugin_id`, `device_id`, `mode`,
  `timeout_ms`
- `CaptureStopRequest`: `capture_plugin_id`, `device_id`, `reason`
- `OperationStatus`: `ok`, `runtime_state`, `message`,
  `retry_budget_remaining`
- `WorkerHeartbeat`: `worker_id`, `health`, `missed_heartbeats`,
  `timestamp_ns`
- `WorkerLog`: `worker_id`, `level`, `message`, `timestamp_ns`
- `PluginLoadResult`: `plugin_id`, `loaded`, `runtime_state`, `error_code`,
  `error_message`
- `DiagnosticsExportRequest`: `include_sections`, `include_recent_logs`
- `DiagnosticsExportResponse`: `artifact_path`, `summary`

The PRD runtime budgets apply to this surface:

- default unary timeout: 750 ms
- heartbeat interval: 500 ms
- worker marked `DEGRADED` after 2 missed heartbeats
- worker escalates after 3 consecutive missed heartbeats

Generated Python modules should be placed under `src/aetherflow/proto/`.
Rebuild them with `uv run python -m tools.build_assets`.

## Timeouts And Retry Posture

All control-plane RPCs default to a 750 ms unary timeout unless explicitly
overridden by the caller.

<!-- prettier-ignore-start -->
| RPC                      | Timeout | Retry Posture                             |
|--------------------------|---------|-------------------------------------------|
| `StartCapture`           | 750 ms  | Retry once on transient transport errors. |
| `StopCapture`            | 750 ms  | Retry once on transient transport errors. |
| `ReportHeartbeat`        | 750 ms  | No automatic retries.                     |
| `ForwardWorkerLog`       | 750 ms  | No automatic retries.                     |
| `ReportPluginLoadResult` | 750 ms  | Retry once on transient transport errors. |
| `ExportDiagnostics`      | 750 ms  | No automatic retries.                     |
<!-- prettier-ignore-end -->

Contract notes:

- `timeout_ms` on `StartCapture` lets the caller request a shorter budget, but
  the default contract remains 750 ms unless explicitly overridden.
- `retry_budget_remaining` in `OperationStatus` is the authoritative field for
  communicating remaining transient retry allowance after a unary RPC returns.
- `tests/contracts/test_execution_contracts.py` currently asserts string presence
  for selected capture control-plane `message` and `rpc` entries in
  `proto/capture.proto` (for example `PluginLoadResult` and unary RPCs such as
  `StartCapture` / `StopCapture` that return `OperationStatus` in the proto). It
  does not assert every frozen type (for example `DiagnosticsExportResponse` is
  not part of that substring list), and it does not independently verify each
  field name—those remain documentation and codegen responsibilities.
