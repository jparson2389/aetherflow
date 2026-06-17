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
| `H1` `EnvironmentManager` lacks full environment orchestration            | `delivery-packaging gap`  | Managed environment roots, requirements files, deletion, and disk measurement now exist; uv/venv repair flows remain packaging work. |
| `H2` worker supervision is not fully wired through packaged runtime IPC   | `host-supervision gap`    | Native process supervision and a C++ `CaptureControl` gRPC service now exist; packaged host startup, plugin lifecycle wiring, watchdog events, and shell endpoint discovery remain runtime work. |
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
- `src/aetherflow/core/ipc/` — Python-side IPC client wrapper for the frozen
  `CaptureControl` surface. It can talk to the native C++ gRPC service; packaged
  host startup and endpoint discovery remain runtime integration work.
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
| Module                                     | Problem                                                               | Retirement plan                                           |
|--------------------------------------------|-----------------------------------------------------------------------|-----------------------------------------------------------|
| `src/aetherflow/core/worker_supervisor.py` | Demoted to read-only host state view; no Python `WorkerSupervisor` alias remains | Not retired. Retire only after shell state flows directly through a real host IPC endpoint, or explicitly retain as a state-view DTO. |
| `src/aetherflow/core/env_manager.py`       | Runtime environment metadata, filesystem creation/deletion, and disk measurement; uv/venv repair remains missing | Implement real uv/venv preparation and repair before managed workload packaging is complete. |
| `src/aetherflow/core/bundle_installer.py`  | Python-side archive install duplicates host-managed install path      | Supersede with host-managed installer before first delivery claims host-owned install. |
| `src/aetherflow/core/plugin_system.py`     | Python-side frozen ABI mirror still imported by contract tests; native host owns real plugin lifecycle | Not retired after task 3.3. Retire or narrow only after native plugin loader coverage no longer depends on the Python mirror. |

<!-- prettier-ignore-end -->

### Stub and Placeholder Component Inventory (2.10)

Components that are not real delivery units yet. Each is marked with its
required disposition before shipping.

<!-- prettier-ignore-start -->
| Component                                     | Current state                                                                                          | Disposition                                                                                                   |
|-----------------------------------------------|--------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------|
| `src/aetherflow/core/ipc/__init__.py`         | Python client wrapper exists and is proven against the native C++ `CaptureControl` gRPC service; packaged endpoint discovery is not wired | **implement before ship** — shell and workers must discover and use the host-served endpoint in the packaged runtime |
| `src/aetherflow/vision/obs_capture.py`        | Fixed-configuration marker only; no IPC forwarding                                                     | **implement before ship** — `OBSCapture.dll` is a declared plugin; Python side must forward lifecycle events  |
| `src/aetherflow/core/env_manager.py`          | Runtime root, requirements, delete, and disk measurement implemented; uv/venv operations still pending | **implement before ship** — managed Python workload preparation depends on full environment repair operations |
| `src/aetherflow/input/playstation.py`         | Descriptor model only; no OS-level I/O                                                                 | **exclude from first delivery tree** — DS4Input/DS5Input native plugins own PlayStation handling              |
| `src/aetherflow/input/xinput.py`              | Descriptor model only; no OS-level I/O                                                                 | **exclude from first delivery tree** — XInputInput native plugin owns XInput handling                         |
| `src/aetherflow/output/virtual_controller.py` | State model only; no signed ViGEm driver integration                                                   | **exclude from first delivery tree** — ViGEmOutput native plugin owns virtual controller output               |
| `src/aetherflow/output/device_masking.py`     | State model only; no driver integration                                                                | **exclude from first delivery tree** — owned by ViGEmOutput and XInputInput native plugins                    |
<!-- prettier-ignore-end -->

---

## Host Native Supervision Surface Inventory (3.1)

### Available native surface

- `include/supervisor.hpp` declares the host-authoritative
  `IWorkerSupervisor` boundary for supervised runtime units. It covers
  `StartUnit`, `RegisterDependency`, `RestartUnit`, `StopUnit`,
  `RecordHeartbeat`, `RecordMissedHeartbeat`, `RecordCrash`,
  `EnforceRestartBudget`, `GetSnapshot`, `GetSnapshots`, and `GetState`.
- `host/supervisor.cpp` contains a concrete native supervision state machine
  with per-unit state, restart counters, missed-heartbeat tracking, process
  launch hooks, process termination hooks, and restart-budget enforcement.
  `StartUnit` requires an OS process launcher path and rejects
  in-memory/thread-only supervision targets. Failed or stopped units degrade
  only their registered direct dependents; unrelated units keep their current
  runtime state. `RestartUnit` relaunches only a recovering unit from its
  stored launch specification and refuses budget-exhausted units.
- `include/capture_control.hpp` and `host/capture_control.cpp` expose the
  host-side `CaptureControlEndpoint` adapter for the frozen control-plane
  operations: capture start/stop, worker heartbeat, worker log forwarding,
  plugin load results, and diagnostics export.
- `include/capture_control_service.hpp`,
  `host/capture_control_service.cpp`, and `host/capture_control_server.cpp`
  expose a native C++ gRPC service and runnable server binary backed by
  `CaptureControlEndpoint`.
- `CMakeLists.txt` builds the native supervisor, control-plane adapter, generated
  C++ protobuf/gRPC stubs, native gRPC service, and
  `aetherflow_capture_control_server` binary when protobuf and gRPC C++ are
  installed.
- `include/plugin_system.hpp` defines the native plugin ABI surface for plugin
  identity, policy, signature policy, load decisions, plugin types, and runtime
  states.
- `host/native_harness.cpp` validates that the native headers expose the
  expected plugin ABI, runtime states, supervisor API names, restart-budget
  constants, and frozen `CaptureControl` RPC names.
- `host/README.md` states that C++ runtime and bridge code belongs under
  `host/`, while public ABI and contract headers belong under `include/`.

### Concrete gaps against target host-supervisor model

- The native gRPC service exists, but packaged host startup does not yet launch
  it, publish its endpoint, or provide shell/worker endpoint discovery.
- There is no native plugin loader lifecycle integration that calls the
  supervisor as plugins register, start, unload, crash, recover, or exhaust
  reload budgets.
- ~~There is no watchdog loop that polls or receives process liveness events
  and converts missed heartbeats or process exits into authoritative supervisor
  updates.~~ Closed (3.5): `IWorkerSupervisor::PollProcessLiveness()` converts a
  dead OS process into an authoritative crash, and `WorkerWatchdog`
  (`host/supervisor.cpp`) drives it on a fixed interval. POSIX `IsAlive()` now
  reaps zombies via `waitpid(WNOHANG)` so an exited child is detected rather
  than reported alive. Workers are isolated processes only — `StartUnit` rejects
  launcher-less (thread-only) targets.
- Process restart launch policy is not implemented end-to-end: the state
  machine records recoverable crashes, but no host-owned relaunch path binds
  the restart budget to isolated worker or plugin process creation.
- Shell-facing state export remains indirect because Python currently mirrors
  host-shaped reports in `WorkerStateView`; the host still needs a stable
  runtime-state export that the shell can consume without synthesizing
  supervision decisions.

### Concrete control-plane wiring deltas

These are the specific, verifiable wiring gaps between the native supervisor
surface and the frozen `CaptureControl` adapter. Each must be closed in 3.3+;
none requires a frozen-contract change.

<!-- prettier-ignore-start -->
| Delta | Location | Blocked capability | Status |
|-------|----------|--------------------|--------|
| No gRPC path reaches `RecordMissedHeartbeat` or `RecordCrash`; `WorkerHeartbeat.missed_heartbeats` is ignored and `ReportHeartbeat` always calls `RecordHeartbeat`. | `host/capture_control.cpp` (`ReportHeartbeat`) | 3.2.3, 3.2.4 | Closed (3.3) — `ReportHeartbeat` now drives `RecordMissedHeartbeat` per reported missed tick so the host computes the resulting state; zero missed ticks records a clean heartbeat. |
| `OperationStatus.retry_budget_remaining` is defined in the proto but never populated (always 0). | `host/capture_control.cpp` | 3.2.5 | Closed (3.3) — derived host-side as `max_restarts - restarts_in_window` via `UnitSnapshot.max_restarts`; populated on start/stop/heartbeat responses. |
| `StopCapture` hardcodes a 250 ms grace period; the gRPC caller cannot pass a custom grace. | `host/capture_control.cpp` (`StopCapture`) | 3.2.2 | Deferred (3.3) — frozen `CaptureStopRequest` has no grace field; a custom grace cannot be plumbed without a proto change. Behavior left unchanged. |
| No dedicated health-query RPC exists; runtime state is returned only as a side effect of other RPCs. | `proto/capture.proto` adapter in `host/capture_control_service.cpp` | 3.2.6 | Deferred — adding a query RPC requires a frozen-proto change; out of 3.3 scope. |
| gRPC service maps every RPC to `grpc::Status::OK` even when `OperationStatus.ok == false`. | `host/capture_control_service.cpp` | all | Closed (3.3) — deliberate: gRPC status reflects transport health, `OperationStatus.ok` (frozen message field) reflects the host decision. Documented inline in `WriteStatus`. |
| `StopUnit` transitions a stopped unit to `kFailed`; there is no distinct `kStopped` state to distinguish an intentional stop from a crash. | `host/supervisor.cpp` (`StopUnit`) | 3.2.2, 3.2.6 | Deferred (3.3) — a `kStopped` value requires editing the frozen `RuntimeState` enum in `include/plugin_system.hpp`; `test_native_harness.py` also asserts `StopCapture → "FAILED"`. Behavior left unchanged. |
| `RegisterDependency` is C++-only; no gRPC RPC exposes dependency registration. | `host/capture_control.cpp` | 3.6 | Partial — `RegisterDependencySpec` + `ApplyDependencyManifest()` bind manifest edges to live `UnitId`s and are contract-tested, but no native plugin loader drives plugin-crash → supervisor → capability-unload; `ReportPluginLoadResult` is append-only. |
| Python `WorkerHealth` enum lacks `LOCKED`/`GRACE` states that the C++ `RuntimeState` enum carries, so the mirror cannot represent every host state. | `src/aetherflow/core/worker_supervisor.py` | 3.2.6 | Open — tracked for 3.8/4.x shell-state work; not in 3.3–3.6 scope. |
<!-- prettier-ignore-end -->

### 3.3 deliberate decisions (frozen-contract constrained)

- **No `kStopped` state.** `RuntimeState` lives in the Phase-0 frozen
  `include/plugin_system.hpp`. Introducing a `kStopped` value is an ABI change
  and is out of bounds. An intentional `StopUnit` therefore continues to resolve
  to `kFailed`, matching the frozen `test_native_harness.py` expectation
  (`StopCapture → runtime_state == "FAILED"`).
- **Hardcoded 250 ms stop grace retained.** The frozen `CaptureStopRequest`
  message carries no grace-period field, so a caller-supplied grace cannot be
  plumbed through the control plane without a proto change. The native
  `StopUnit(id, grace_period)` API still accepts a custom grace for host-internal
  callers; only the gRPC-facing default is fixed at 250 ms.
- **gRPC status vs. `OperationStatus.ok`.** Transport status stays
  `grpc::Status::OK` for any delivered+processed request; the application
  outcome is carried in the frozen `OperationStatus` message so that
  `runtime_state`, `message`, and `retry_budget_remaining` are never discarded
  by a non-OK gRPC status.

---

## Host-side Supervisor API Design (3.2)

The host-side supervisor API is the native authority boundary. It must remain
small: callers request lifecycle actions or submit observed runtime events, and
the supervisor returns host-owned state. Shell and worker processes reach this
boundary through a gRPC `CaptureControl` adapter; they do not call or duplicate
the state machine directly.

<!-- prettier-ignore-start -->
| Task ref | Required behavior                 | Native API contract                         | gRPC `CaptureControl` adapter responsibility                                                                   |
|----------|-----------------------------------|---------------------------------------------|----------------------------------------------------------------------------------------------------------------|
| 3.2.1    | start worker/plugin runtime unit  | `StartUnit(unit_name, launcher_path, args)` | Translate host-approved launch requests into native unit starts and return the assigned unit identifier/state. |
| 3.2.2    | stop worker/plugin runtime unit   | `StopUnit(id, grace_period)`                | Translate stop/unload requests into bounded process termination for the target unit only.                      |
| 3.2.3    | record heartbeat                  | `RecordHeartbeat(id)`                       | Accept worker heartbeat reports and update the native missed-heartbeat counter/state.                          |
| 3.2.4    | record crash or abnormal exit     | `RecordCrash(id, ExitStatus)`               | Convert watchdog/process-exit events into crash reports with exit code and abnormal-exit classification.       |
| 3.2.5    | enforce restart budget            | `EnforceRestartBudget(id)`                  | Expose manual reload/retry decisions through host-owned budget evaluation, never Python-side counters.         |
| 3.2.6    | surface runtime health state      | `GetSnapshot(id)` and `GetState(id)`        | Return authoritative runtime state snapshots for shell HUD, diagnostics, logs, and admin surfaces.             |
| 3.6      | isolate direct dependent failures | `RegisterDependency(dependent, dependency)` | Preserve direct dependency impact without degrading unrelated plugin or shell units.                           |
| 3.7      | restart target runtime unit       | `RestartUnit(id)`                           | Relaunch only the recovering unit through the host-owned launch spec and return budget-exhaustion refusal.     |
| 3.8      | export all runtime health state   | `GetSnapshots()`                            | Provide a stable aggregate state export so shell clients do not synthesize the runtime unit set.               |
<!-- prettier-ignore-end -->

Design constraints for implementation work:

- Unit identifiers are host-assigned `UnitId` values and remain stable until the
  unit is torn down or manually reloaded.
- Runtime state precedence and restart-budget transitions stay in the native
  supervisor; Python consumers may render snapshots but must not infer
  transitions.
- Direct dependency impact is explicit: a dependency failure degrades only the
  registered direct dependents and leaves unrelated runtime units unchanged.
- **3.6 dependency wiring (frozen-proto workaround).** Plugin dependency graphs
  are declared host-side from a static unit manifest, not over gRPC: the frozen
  `CaptureControl` service has no dependency-registration RPC and none was added.
  `CaptureControlEndpoint::RegisterDependencySpec(dependent, dependency)` records
  manifest edges by runtime id; `ApplyDependencyManifest()` binds each edge to
  the live `UnitId`s and calls the supervisor's `RegisterDependency` once both
  endpoints are started (idempotent, re-appliable). A crashed unit therefore
  degrades only its declared direct dependents while the shell-equivalent root
  and unrelated units stay `RUNNING`
  (`test_native_capture_control_registers_dependency_from_manifest`).
- Plugin lifecycle integration must call these methods for plugin process
  units and their direct worker/helper units, preserving failure isolation
  between unrelated units.
- The gRPC `CaptureControl` adapter is a transport layer only. It forwards
  validated commands and reports to the native supervisor and serializes the
  resulting host-owned state.

---

## Feature Delivery Unit Inventory (5.0)

Section 5.0 converts the current input, output, and vision feature areas into
delivery units that the package can either ship, explicitly defer, or require
implementation before shipment. A feature is considered shippable only when it
has a concrete packaged artifact and a mapped runtime launch path through the
host-owned plugin loader or helper-process launcher.

### Feature Area Inventory (5.1)

- `src/aetherflow/input/` contains the KBM input helper implementation
  (`kbm.py`) and its event/listener/mapping/pipeline support modules. It also
  contains XInput and PlayStation descriptor models that do not perform
  OS-level controller I/O.
- `src/aetherflow/output/` contains shell-facing virtual-controller and device
  masking state models. Driver-backed output remains a native plugin/runtime
  concern and is not implemented by these Python modules.
- `src/aetherflow/vision/` contains OpenCV capture mode support, premium
  Media Foundation/DirectShow catalog and entitlement gating, and an OBS
  fixed-configuration marker that still lacks real lifecycle forwarding.

### Feature Delivery Unit Records (5.3)

<!-- prettier-ignore-start -->
| Feature/source                                                                                           | Current implementation                                            | Delivery decision                      | Packaged artifact                                                                                       | Runtime dependencies in `lib/`                                                                | Translation asset placement                                                | Trust and entitlement rules                                                                                   | Reload/failure behavior                                                                        | Runtime launch path                                                                   | First delivery state             |
|----------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------|----------------------------------------|---------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------|----------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------|----------------------------------|
| KBM input helper: `src/aetherflow/input/kbm.py`; `events.py`; `listener.py`; `mapping.py`; `pipeline.py` | Real OS listener, ingestion pipeline, mapping pipeline, telemetry | packaged Python helper/runtime payload | `lib/py/aetherflow/input/{kbm,events,listener,mapping,pipeline}.py`                                     | `lib/py/aetherflow/core/profiles.py`; managed workload dependency `pynput`; profile data APIs | Not applicable                                                             | Built-in first-party helper; no premium entitlement; launched only by host-approved worker spec               | Host restarts or unloads the KBM helper process only; shell and unrelated plugins remain alive | `lib/cv_python_host/CVPythonHost.exe --module aetherflow.input.kbm`                   | implement before ship            |
| OpenCV capture helper: `src/aetherflow/vision/opencv_capture.py`                                         | Device and mode provider with supported-mode behavior             | packaged Python helper/runtime payload | `lib/py/aetherflow/vision/opencv_capture.py`                                                            | `lib/cv_cpp/`; OpenCV runtime DLLs; `lib/py/aetherflow/core/shared_memory_layout.py`          | `lib/translations/plugins/OpenCVCapture/`                                  | Built-in capture helper; no premium entitlement; host owns capture start/stop authority                       | Capture helper crash degrades capture surface only; host can restart the helper process        | `lib/cv_python_host/CVPythonHost.exe --module aetherflow.vision.opencv_capture`       | implement before ship            |
| CV Python host launcher for input/capture helpers                                                        | Helper executable contract for worker modules                     | packaged helper executable             | `lib/cv_python_host/CVPythonHost.exe`                                                                   | `lib/py/`; `lib/cv_cpp/`; Qt/runtime DLLs only if the helper process declares them            | Not applicable                                                             | First-party signed helper executable; may launch only package-declared modules                                | Host supervisor owns process lifetime, heartbeat budget, restart, and escalation               | `lib/cv_python_host/CVPythonHost.exe`                                                 | implement before ship            |
| Media Foundation capture: `src/aetherflow/vision/mf_capture.py`                                          | Premium catalog and entitlement gate for native capture           | native plugin DLL                      | `plugins/MFCapture.dll`; shell support in `lib/py/aetherflow/vision/mf_capture.py`                      | Native capture support DLLs under `lib/`; optional `lib/cv_cpp/` interop if declared          | `lib/translations/plugins/MFCapture/`                                      | Built-in premium plugin; must call `EntitlementStore.evaluate(...)`; locked plugins do not register providers | Failed plugin unloads direct dependents only; manual reload targets `MFCapture.dll`            | `plugins/MFCapture.dll` through the host plugin loader                                | implement before ship            |
| DirectShow capture: `src/aetherflow/vision/ds_capture.py`                                                | DirectShow premium catalog variant backed by MF gating            | native plugin DLL                      | `plugins/DirectShowCapture.dll`; shell support in `lib/py/aetherflow/vision/ds_capture.py`              | Native DirectShow support DLLs under `lib/`; optional `lib/cv_cpp/` interop if declared       | `lib/translations/plugins/DirectShowCapture/`                              | Built-in premium plugin; must call `EntitlementStore.evaluate(...)`; locked plugins do not register providers | Failed plugin unloads direct dependents only; manual reload targets `DirectShowCapture.dll`    | `plugins/DirectShowCapture.dll` through the host plugin loader                        | implement before ship            |
| OBS capture: `src/aetherflow/vision/obs_capture.py`                                                      | Fixed-configuration marker only; lifecycle forwarding incomplete  | native plugin DLL                      | `plugins/OBSCapture.dll`; shell support must be implemented before inclusion                            | OBS/native capture support DLLs under `lib/`; shared-memory frame layout in `lib/py/`         | `lib/translations/plugins/OBSCapture/`                                     | Built-in plugin; no premium entitlement unless later declared                                                 | Must degrade only OBS capture and its direct dependents; not shippable until wired             | `plugins/OBSCapture.dll` through the host plugin loader                               | implement before ship            |
| XInput controller descriptor: `src/aetherflow/input/xinput.py`                                           | Descriptor only; no OS-level controller I/O                       | excluded or deferred capability        | Python descriptor excluded; future native target is `plugins/XInputInput.dll`                           | Native XInput runtime support under `lib/` when plugin exists                                 | `lib/translations/plugins/XInputInput/`                                    | Built-in native input plugin once implemented; no premium entitlement                                         | Failure must degrade only XInput input surface                                                 | Future `plugins/XInputInput.dll` through the host plugin loader                       | exclude from first delivery tree |
| PlayStation controller descriptor: `src/aetherflow/input/playstation.py`                                 | Descriptor only; no OS-level controller I/O                       | excluded or deferred capability        | Python descriptor excluded; future native targets are `plugins/DS4Input.dll` and `plugins/DS5Input.dll` | Native HID/controller support DLLs under `lib/` when plugins exist                            | `lib/translations/plugins/DS4Input/`; `lib/translations/plugins/DS5Input/` | Built-in native input plugins once implemented; no premium entitlement                                        | Failure must degrade only the matching PlayStation input surface                               | Future `plugins/DS4Input.dll` / `plugins/DS5Input.dll` through the host plugin loader | exclude from first delivery tree |
| Virtual output state: `src/aetherflow/output/virtual_controller.py`                                      | Shell-facing driver status model; no signed ViGEm integration     | shell-only module                      | `lib/py/aetherflow/output/virtual_controller.py`                                                        | Shell IPC/status models in `lib/py/aetherflow/core/`; native ViGEm plugin when implemented    | Not applicable                                                             | Shell renders host-reported output state; it must not load a driver directly                                  | Output failure degrades output surface only; shell remains alive                               | PySide shell imports from `lib/py/aetherflow/output/virtual_controller.py`            | exclude from first delivery tree |
| Device masking state: `src/aetherflow/output/device_masking.py`                                          | Shell-facing masking state model; no driver integration           | shell-only module                      | `lib/py/aetherflow/output/device_masking.py`                                                            | Shell IPC/status models in `lib/py/aetherflow/core/`; native masking driver when implemented  | Not applicable                                                             | Shell renders host-reported masking state; it must not apply masking directly                                 | Masking failure degrades output/input masking surface only                                     | PySide shell imports from `lib/py/aetherflow/output/device_masking.py`                | exclude from first delivery tree |
<!-- prettier-ignore-end -->

### Stub and Exclusion Disposition (5.4)

- `src/aetherflow/vision/obs_capture.py` remains `implement before ship`; it
  may not be marked `ship` until the OBS lifecycle path forwards start/stop,
  heartbeat, logs, and failure state through the host-owned control plane.
- `src/aetherflow/input/xinput.py` and
  `src/aetherflow/input/playstation.py` are excluded from the first delivery
  tree as Python runtime payloads. The shippable implementations must be
  native plugin DLLs with host loader records.
- `src/aetherflow/output/virtual_controller.py` and
  `src/aetherflow/output/device_masking.py` remain shell-facing state models,
  not driver implementations. They may ship only as shell support after a
  native output plugin is mapped; they are excluded as standalone delivery
  units for the first delivery tree.

### Shipped Feature Validation Rule (5.7)

Any feature row with `First delivery state` set to `ship` must have:

- a concrete `Packaged artifact`;
- a `Runtime launch path` through the host plugin loader or
  `CVPythonHost.exe`;
- a current implementation description that is not a marker, descriptor-only
  scaffold, or state-only model;
- declared trust, entitlement, dependency, translation, and reload behavior.

Rows that fail any of those checks must be marked `implement before ship` or
`exclude from first delivery tree`, not `ship`.

As of the 2026-05-01 integrity audit, no feature row is marked `ship` because
the package-required helper executable, native plugin DLLs, host plugin-loader
integration, and first-delivery manifest validation are not yet present in the
repo. A later row may be changed to `ship` only when the artifact exists or is
produced by the packaging pipeline and the validation rule checks the staged
path directly.
