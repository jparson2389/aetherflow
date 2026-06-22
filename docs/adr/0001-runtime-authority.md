# ADR 0001: Host-Authoritative Runtime Supervision

## Status

Accepted.

## Context

Aetherflow combines a native host, native plugins, Python workers, and a PySide6
shell. Plugins and workers can fail independently, but the host and shell must
remain available so users can see degraded state, reload affected features, and
export diagnostics.

The detailed decision is recorded in
`docs/architecture/runtime-authority-decision.md`.

## Decision

`Aetherflow.exe` is the supervisor of record. Supervision authority, plugin
lifecycle authority, IPC endpoint ownership, heartbeat handling, restart
budgets, escalation, and reload decisions live at the native host boundary.

The PySide6 shell is a durable client and rendering surface. Python workers run
out of process. Python code may render, relay, or adapt host-reported state, but
must not become the runtime authority.

## Consequences

- Host-owned state is authoritative for lifecycle and failure handling.
- Python shell and worker code communicate with the host through gRPC and shared
  memory only.
- Plugin or worker failure must degrade only the affected feature surface.
- New code must not add in-process C++/Python embedding, direct lifecycle
  decisions in the shell, or bypasses around the frozen control-plane contract.

## References

- `docs/architecture/runtime-authority-decision.md`
- `docs/architecture/delivery-architecture-alignment-notes.md`
- `docs/PRD.md`
- `docs/PLAN.md`
