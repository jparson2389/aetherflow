# Aetherflow Context

## Domain

Aetherflow is a Windows-first controller adapter host with a microkernel plugin
architecture. The product coordinates native plugins, out-of-process Python
workers, a PySide6 shell, and entitlement-aware feature loading.

The core domain constraint is failure isolation: the host and shell must remain
operational when a plugin or worker fails, and affected features degrade without
pulling unrelated surfaces down.

## Canonical Sources

Read these before changing architecture, delivery, packaging, supervision,
worker, IPC, entitlement, or plugin behavior:

- `docs/PRD.md` - product requirements and frozen contract expectations.
- `docs/PLAN.md` - implementation sequence, validation policy, and current
  delivery constraints.
- `docs/architecture/runtime-authority-decision.md` - host-authoritative
  supervision model and shell durability.
- `docs/architecture/delivery-runtime-layout.md` - packaged runtime tree and
  mutable managed-runtime placement.
- `docs/architecture/delivery-architecture-alignment-notes.md` - delivery
  architecture alignment notes, Python module classification, and transitional
  component disposition.
- `proto/capture.proto` - frozen gRPC control-plane contract.
- `include/plugin_system.hpp` - native plugin ABI and trust boundary.
- `src/aetherflow/core/shared_memory_layout.py` - shared-memory frame layout.
- `src/aetherflow/core/entitlements.py` - entitlement state machine.

## Glossary

- `Aetherflow.exe`: Native host and supervisor of record.
- PySide6 shell: Durable Python UI client and rendering surface. It renders
  host-reported state and must not own runtime supervision.
- Host authority: The native host owns plugin lifecycle, worker lifecycle,
  IPC endpoints, heartbeats, restart budgets, escalation, and reload decisions.
- Plugin: Native extension loaded through the host plugin system. Premium
  plugins may ship locked and must not load without entitlement approval.
- Worker: Out-of-process Python workload that communicates with the host through
  gRPC for control and shared memory for frame data.
- Control plane: gRPC surface defined by `proto/capture.proto`.
- Data plane: Shared-memory frame path defined by
  `src/aetherflow/core/shared_memory_layout.py`.
- Managed runtime: Mutable user-local Python runtime state under
  `%LOCALAPPDATA%/AetherflowProject/Aetherflow/python/`.
- Packaged runtime: The immutable Windows app package tree defined in
  `docs/architecture/delivery-runtime-layout.md`.
- Entitlement: Access state resolved only through
  `EntitlementStore.evaluate(...)`.

## Boundaries

- C++ code belongs only in `host/` and `include/`.
- Python code belongs under `src/aetherflow/`.
- Python and C++ communicate only through IPC; never embed one runtime in the
  other.
- The shell consumes host state; it does not infer or duplicate supervision
  authority.
- Generated gRPC stubs under `src/aetherflow/proto/` are generated artifacts and
  must not be hand-edited.
- Frozen contracts require explicit human sign-off before changes.

## Validation Vocabulary

- Contract tests live under `tests/contracts/`.
- Unit tests live under `tests/unit/`.
- Integration tests live under `tests/integration/`.
- UI tests live under `tests/ui/`.
- Python commands run through `uv run`.
- The repo-owned quality gate is `uv run python -m tools.check_quality`.
