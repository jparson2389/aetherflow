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

Generated Python modules should be placed under `src/aetherflow/core/ipc/`.
