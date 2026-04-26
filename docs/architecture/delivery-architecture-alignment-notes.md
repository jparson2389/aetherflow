# Delivery Architecture Alignment Notes

## Scope

These notes capture the task 1.0 alignment inputs from `docs/PRD.md`,
`AGENTS.md`, and `docs/dev/aetherflow-codebase-review.md`. They lock the
runtime authority model before any supervision or packaging implementation work
continues.

## PRD Requirement Extraction

<!-- prettier-ignore-start -->
| PRD Ref | Exact requirement                                                                                                                                                                                                                                                                                                                                                    | Implementation note                                                                                                                                                                   |
|---------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `§5.1`  | The host contains the plugin loader and registry, service container, UI shell and router, worker supervisor, and IPC endpoints. Everything else ships as plugins or workers.                                                                                                                                                                                         | Supervision authority, plugin lifecycle authority, and IPC endpoint ownership stay on the native host side. Python may render or relay state, but it is not the supervisor of record. |
| `§7.2`  | The minimum control-plane schema covers capture start, capture stop, worker heartbeat, worker log forwarding, plugin load result and load error, plus diagnostics export request and response. Timeout and retry posture must be documented and tested.                                                                                                              | Any shell, admin, or worker-facing Python client must use the frozen `CaptureControl` surface instead of direct in-memory supervisor calls.                                           |
| `§7.4`  | Runtime state precedence is `FAILED > RECOVERING > DEGRADED > RUNNING`. Recoveries and failures degrade only the affected feature surface while unrelated surfaces remain active.                                                                                                                                                                                    | State resolution and restart-budget decisions must come from host-owned runtime state so the shell can display affected-surface-only degradation without inferring local authority.   |
| `§9.1`  | Plugins must declare dependencies, required services, optional UI panels, and worker requirements before lifecycle methods run. Missing entitlements, drivers, workers, or compatible dependencies must block registration rather than crash the host. Failed plugins and direct dependents may unload, but the host shell and unrelated plugins remain operational. | Plugin lifecycle authority belongs to the host boundary. The shell survives failures and only reflects host-reported capability changes.                                              |
| `§9.7`  | All Python scripts and vision processing run out of process. The supervisor handles start, stop, restart, heartbeat, and escalation. UI surfaces worker logs and health state. Worker failure must not crash the host.                                                                                                                                               | Python workers are isolated workloads. Worker supervision authority lives with the host, and the shell consumes logs and health data through IPC.                                     |
| `§10.1` | On plugin crash, unload the plugin, keep the host and shell alive, show HUD `DEGRADED`, show a toast naming the failed plugin, and expose manual reload plus copy-diagnostics actions.                                                                                                                                                                               | Failure UX is shell-rendered but host-authored. Reload actions target the affected plugin only and do not move supervision authority into Python.                                     |
<!-- prettier-ignore-end -->

## AGENTS Conflicts To Resolve

<!-- prettier-ignore-start -->
| Source text                                                                                                                      | Conflict                                                                                                                         | Resolution applied                                                                                          |
|----------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------|
| `src/aetherflow/core/` -> `runtime orchestration, plugin manager, shared logic`                                                  | `§5.1`, `§9.1`, and `§9.7` place runtime supervision and plugin lifecycle authority in the host, not in the Python package tree. | Redefine `src/aetherflow/core/` as shared logic, IPC clients/adapters, and transitional Python integration. |
| No explicit statement that the PySide shell must remain alive when plugins or workers fail                                       | `§9.1`, `§9.7`, and `§10.1` require shell survivability outside plugin and worker failure domains.                               | Add explicit shell survivability guidance to `AGENTS.md`.                                                   |
| No explicit statement that host-owned state is authoritative for start, stop, restart, heartbeat, escalation, and reload budgets | `§5.1`, `§7.4`, and `§9.7` require authoritative host-owned runtime state.                                                       | Add explicit host-authoritative runtime-state guidance to `AGENTS.md` and `docs/PLAN.md`.                   |
<!-- prettier-ignore-end -->

## Critical And High Review Findings Bucketed

<!-- prettier-ignore-start -->
| Finding                                                                   | Bucket                    | Why it belongs there                                                                                                                 |
|---------------------------------------------------------------------------|---------------------------|--------------------------------------------------------------------------------------------------------------------------------------|
| `C1` gRPC/IPC boundary is completely unimplemented                        | `IPC gap`                 | The missing Python client layer means heartbeats, logs, diagnostics, and lifecycle results cannot traverse the frozen control plane. |
| `C2` Contract tests import via `src.aetherflow` instead of `aetherflow`   | `correctness-only defect` | This is a broken canonical-path assertion, but not a supervision or packaging ownership gap.                                         |
| `C3` Manifest revocation and tamper checks are caller-controlled booleans | `correctness-only defect` | The defect weakens trust verification semantics, but it does not define runtime supervision or packaging ownership.                  |
| `H1` `EnvironmentManager` is entirely in-memory                           | `delivery-packaging gap`  | The runtime cannot yet deliver real packaged environment operations, repair flows, or probes.                                        |
| `H2` `WorkerSupervisor` is not wired to real processes                    | `host-supervision gap`    | Restart budgets exist only in Python-local state; the host is not yet supervising real worker processes.                             |
| `H3` ABI requires RSA-3072 while manifest signing uses Ed25519            | `correctness-only defect` | The issue is a frozen-contract mismatch that must be corrected or signed off, but it does not move supervision authority.            |
| `H4` `AuditLog.__post_init__` can crash startup on a corrupted line       | `correctness-only defect` | This is a resilience bug inside startup handling, not an ownership or packaging mapping problem.                                     |
| `H5` Frozen security dataclasses contain mutable list fields              | `correctness-only defect` | This is a trust/correctness issue, not a supervision or packaging authority issue.                                                   |
<!-- prettier-ignore-end -->

## Task 1.0 Outcomes Required

- `Aetherflow.exe` is the supervisor of record.
- The PySide shell is a durable client and rendering surface that survives
  plugin and worker failures.
- Plugins and workers stay outside the shell's critical failure domain.
- Host-owned runtime state is authoritative for start, stop, restart,
  heartbeat, escalation, and reload-budget decisions.

---

## Task 2.0 Supplemental Notes

### Managed Python Runtime Layout (2.8)

The managed Python runtime is **not** part of the packaged root tree. It is
mutable state created on the user's machine by one-click install and the
runtime environment manager. The five canonical path components are:

<!-- prettier-ignore-start -->
| Ref   | Path                                                                             | Purpose                                                                                |
|-------|----------------------------------------------------------------------------------|----------------------------------------------------------------------------------------|
| 2.8.1 | `%LOCALAPPDATA%\AetherflowProject\Aetherflow\python\managed-python\`             | Managed CPython interpreter distribution tree                                          |
| 2.8.2 | `%LOCALAPPDATA%\AetherflowProject\Aetherflow\python\uv.exe`                      | `uv` executable; lives at the managed Python root, not in the packaged root            |
| 2.8.3 | `%LOCALAPPDATA%\AetherflowProject\Aetherflow\python\<workload>\`                 | Per-workload root directory (e.g. `cv\` for computer vision)                           |
| 2.8.4 | `%LOCALAPPDATA%\AetherflowProject\Aetherflow\python\<workload>\.aenv\`           | Per-workload virtual environment; created and owned by the runtime environment manager |
| 2.8.5 | `%LOCALAPPDATA%\AetherflowProject\Aetherflow\python\<workload>\requirements.txt` | Per-workload dependency specification consumed by the runtime environment manager      |
<!-- prettier-ignore-end -->

These paths are entirely separate from the `dist/` packaged tree.
`docs/architecture/delivery-runtime-layout.md` already documents the packaged tree; this note
records the managed runtime tree so agents do not conflate the two.

### Python Module Classification (2.9)

#### Shell-only modules (2.9.1)

Run inside the PySide6 shell process only. Must not duplicate host supervision
logic. Must consume host state via the IPC client layer.

- `src/aetherflow/ui/` — entire UI subsystem
- `src/aetherflow/core/audit_log.py`
- `src/aetherflow/core/capture_metrics.py`
- `src/aetherflow/core/developer_app_checks.py`
- `src/aetherflow/core/diagnostics.py`
- `src/aetherflow/core/diagnostics_export.py`
- `src/aetherflow/core/dotenv_bootstrap.py`
- `src/aetherflow/core/entitlements.py` — consumed via `EntitlementStore.evaluate()` only
- `src/aetherflow/core/ipc/` — Python-side IPC client layer (stub; implement before ship)
- `src/aetherflow/core/oauth.py`
- `src/aetherflow/core/profile_persistence.py`
- `src/aetherflow/core/profiles.py`
- `src/aetherflow/core/resources_client.py`
- `src/aetherflow/core/resources_manifest.py`
- `src/aetherflow/core/runtime_state.py` — user-visible state enum; not the supervisor of record
- `src/aetherflow/core/services.py` — `AppServices` wiring container
- `src/aetherflow/core/settings.py`
- `src/aetherflow/core/verification_report.py`
- `src/aetherflow/plugins/` — catalog, manifest, registry, trust; shell-facing consumers of host state
- `src/aetherflow/security/`
- `src/aetherflow/utils/`

#### Worker and helper modules (2.9.2)

Intended for out-of-process deployment. Must not import shell-only UI code.
Communicate with the host through gRPC and shared memory only.

- `src/aetherflow/vision/opencv_capture.py`
- `src/aetherflow/vision/mf_capture.py`
- `src/aetherflow/vision/ds_capture.py`
- `src/aetherflow/vision/obs_capture.py`
- `src/aetherflow/core/shared_memory_layout.py` — ring buffer contract; no shell logic
- `src/aetherflow/input/events.py`
- `src/aetherflow/input/listener.py`
- `src/aetherflow/input/kbm.py` — KBM OS-level ingestion worker
- `src/aetherflow/input/mapping.py`
- `src/aetherflow/input/pipeline.py`
- `src/aetherflow/input/playstation.py`
- `src/aetherflow/input/xinput.py`
- `src/aetherflow/output/device_masking.py`
- `src/aetherflow/output/virtual_controller.py`

#### Transitional modules to retire (2.9.3)

Currently hold duties that must transfer to the host or real runtime
implementations. Must not be treated as canonical in new code.

<!-- prettier-ignore-start -->
| Module                                     | Problem                                                                       | Retirement plan                                                     |
|--------------------------------------------|-------------------------------------------------------------------------------|---------------------------------------------------------------------|
| `src/aetherflow/core/worker_supervisor.py` | Python-side supervisor of record; supervision authority must move to the host | Demote to read-only IPC state consumer after task 3.4               |
| `src/aetherflow/core/env_manager.py`       | In-memory only; no real disk or runtime operations                            | Replace with real runtime-managed environment operations (task 4.6) |
| `src/aetherflow/core/bundle_installer.py`  | Python-side archive install duplicates host-managed install path              | Supersede with host-managed installer                               |
| `src/aetherflow/core/plugin_system.py`     | Python-side plugin lifecycle; authority belongs to the C++ host               | Retire after task 3.3+                                              |

<!-- prettier-ignore-end -->

### Stub and Placeholder Component Inventory (2.10)

Components that are not real delivery units yet. Each is marked with its
required disposition before shipping.

<!-- prettier-ignore-start -->
| Component                                     | Current state                                              | Disposition                                                                                                  |
|-----------------------------------------------|------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------|
| `src/aetherflow/core/ipc/__init__.py`         | Empty module; no control-plane client operations           | **implement before ship** — required for shell to communicate over the frozen `CaptureControl` surface       |
| `src/aetherflow/vision/obs_capture.py`        | Fixed-configuration marker only; no IPC forwarding         | **implement before ship** — `OBSCapture.dll` is a declared plugin; Python side must forward lifecycle events |
| `src/aetherflow/core/env_manager.py`          | In-memory records only; no real disk or runtime operations | **implement before ship** — managed Python workload preparation depends on real environment operations       |
| `src/aetherflow/input/playstation.py`         | Descriptor model only; no OS-level I/O                     | **exclude from first delivery tree** — DS4Input/DS5Input native plugins own PlayStation handling             |
| `src/aetherflow/input/xinput.py`              | Descriptor model only; no OS-level I/O                     | **exclude from first delivery tree** — XInputInput native plugin owns XInput handling                        |
| `src/aetherflow/output/virtual_controller.py` | State model only; no signed ViGEm driver integration       | **exclude from first delivery tree** — ViGEmOutput native plugin owns virtual controller output              |
| `src/aetherflow/output/device_masking.py`     | State model only; no driver integration                    | **exclude from first delivery tree** — owned by ViGEmOutput and XInputInput native plugins                   |
<!-- prettier-ignore-end -->
