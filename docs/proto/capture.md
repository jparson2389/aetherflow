# Capture Control Plane

`proto/capture.proto` defines the minimum frozen control-plane contract for:

- capture start and stop
- worker heartbeats
- worker log forwarding
- plugin load result reporting
- diagnostics export requests

The PRD runtime budgets apply to this surface:

- default unary timeout: 750 ms
- heartbeat interval: 500 ms
- worker marked `DEGRADED` after 2 missed heartbeats
- worker escalates after 3 consecutive missed heartbeats

Generated Python modules should be placed under `src/aetherflow/proto/`.

## Timeouts And Retry Posture

All control-plane RPCs default to a 750 ms unary timeout unless explicitly
overridden by the caller.

| RPC | Timeout | Retry Posture |
| --- | --- | --- |
| `StartCapture` | 750 ms | Retry once on transient transport errors. |
| `StopCapture` | 750 ms | Retry once on transient transport errors. |
| `ReportHeartbeat` | 750 ms | No automatic retries. |
| `ForwardWorkerLog` | 750 ms | No automatic retries. |
| `ReportPluginLoadResult` | 750 ms | Retry once on transient transport errors. |
| `ExportDiagnostics` | 750 ms | No automatic retries. |
