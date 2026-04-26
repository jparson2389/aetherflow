# Runtime Authority Decision

## Status

Accepted on March 31, 2026 for delivery architecture alignment task 1.0.

## Context

The PRD defines a microkernel host that owns plugin lifecycle, worker
supervision, and IPC endpoints. The existing repo guidance still left room to
read Python `core/` code as the runtime orchestrator, which is incompatible
with the PRD's host-authoritative failure model.

## Decision

1. `Aetherflow.exe` is the supervisor of record.
2. The PySide shell is a durable client and rendering surface. It must remain
   alive when plugins or workers fail.
3. Plugins and workers run outside the shell's critical failure domain.
4. Host-owned state is authoritative for start, stop, restart, heartbeat,
   escalation, and reload-budget decisions.

## Consequences

- `host/` and `include/` own supervision and plugin lifecycle authority.
- `src/aetherflow/core/ipc/` is the Python client bridge to authoritative host
  state.
- `src/aetherflow/core/worker_supervisor.py` is transitional and must become a
  thin adapter or be retired once host-owned supervision is in place.
- Shell HUD, diagnostics, and reload actions render host-reported state rather
  than inferring local supervision authority.
