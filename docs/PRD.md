# Product Requirements Document (PRD) — Aetherflow (Windows v1)

**Document Date:** March 8, 2026  
**Status:** Draft v1.7 (Executable delivery revision)  
**Platform (v1):** Windows only  
**UI Tech:** Qt for Python (PySide6 6.9.x)  
**Runtime:** Native DLL plugins + out-of-process Python workers via gRPC and
shared memory  
**Monetization:** Tiered entitlements with shipped-but-locked premium plugins  
**Core thesis:** Microkernel host where everything is a plugin

---

## 1) Executive Summary

Aetherflow is a Windows-first controller adapter ecosystem for gaming. The host
must stay responsive and operational even when plugins or workers fail. Premium,
capture, resource, and worker features all ship through explicit contracts so an
agent can build and validate the product without relying on external upload
references or undocumented behavior.

This PRD is self-contained. All normative requirements, performance budgets,
trust requirements, UI failure flows, and contract expectations needed for
implementation are expressed here or in the frozen contract files referenced by
this document.

---

## 2) G3 Framework

### Guidelines

- Core thesis: microkernel host where everything is a plugin
- Platform: Windows only for v1
- Tech stack: C++20 in `host/` and `include/`, Python 3.12 in `src/aetherflow/`
- IPC: gRPC control plane + shared memory data plane
- Monetization: premium plugins ship with the product but stay locked until
  entitlements allow load
- Priority order when requirements conflict:
  `Host Stability > Security/Signing > Feature Completeness > Performance > UX`

### Guidance

- Ambiguity defaults to the most restrictive safe behavior.
- Frozen contracts may not change after their freeze point without a documented
  breaking-change entry and human sign-off.
- TDD is mandatory for implementation work.
- File paths named in `docs/PLAN.md` are canonical and must not drift.

### Guardrails

- NEVER load a premium plugin DLL without valid or GRACE entitlement.
- NEVER execute unsigned, tampered, expired, or revoked native plugins or
  protected artifacts.
- NEVER place C++ code under `src/`; C++ belongs only in `host/` and `include/`.
- NEVER bypass gRPC for worker-to-host control traffic.
- ALWAYS use Loguru, type hints, and Google-style docstrings in public Python
  functions.
- ALWAYS run `uv run ruff check .` and `uv run pytest` before marking work done.

---

## 3) Goals And Non-Goals

### 3.1 Goals

- Easy setup: install, sign in, and achieve baseline mapping quickly.
- Deterministic primary I/O path.
- Capture that exposes only supported modes and validates 60 FPS baseline.
- Safe out-of-process vision, scripting, and worker supervision.
- In-app environment management with one-click signed bundle install.
- Signed Online Resources with entitlement-aware lock states.
- Premium gating that keeps locked features present but unloadable.

### 3.2 Non-Goals

- macOS or Linux support
- In-app model training pipelines
- Unsigned third-party native plugin support
- Anti-cheat bypass or covert cheating scenarios
- Protected model cryptosystem implementation in v1

---

## 4) Roles

| Role                 | Access Scope                         | Entitlement Level | Hard Boundaries                        |
| -------------------- | ------------------------------------ | ----------------- | -------------------------------------- |
| Power Gamer          | Profiles, mapping, fast switching    | Free / Pro        | No admin, no env management            |
| Vision/ML Tinkerer   | Capture config, envs, resources      | Pro / Vision      | No billing or user admin               |
| Accessibility Modder | Automation primitives, calibration   | Pro               | No premium capture without entitlement |
| Admin/Operator       | Entitlements, users, audit, sessions | Enterprise        | Full admin scope                       |

---

## 5) Architecture And Frozen Contracts

### 5.1 Microkernel Host

The host contains only:

- plugin loader and registry
- service container
- UI shell and router
- worker supervisor and IPC endpoints

Everything else ships as plugins or workers.

### 5.2 Sensing vs Acting

- Sensing: capture, preview, metrics, inference
- Acting: virtual output and future bridge output

### 5.3 Frozen Contracts

| File                                          | Freeze Point   | Breaking Change Log                     |
| --------------------------------------------- | -------------- | --------------------------------------- |
| `include/plugin_system.hpp`                   | End of Phase 0 | `docs/breaking-changes/abi.md`          |
| `proto/capture.proto`                         | End of Phase 0 | `docs/breaking-changes/proto.md`        |
| `src/aetherflow/core/shared_memory_layout.py` | End of Phase 0 | `docs/breaking-changes/shmem.md`        |
| `src/aetherflow/core/entitlements.py`         | End of Phase 4 | `docs/breaking-changes/entitlements.md` |

If a frozen contract must change:

1. Stop work.
2. Report `FROZEN CONTRACT MODIFICATION REQUIRED: <file> — <reason>`.
3. Wait for human instruction.

---

## 6) Runtime Budgets And Operational SLOs

These budgets are normative for v1 on supported Windows 11 hardware.

### 6.1 Primary Path Latency

- Input-to-output latency median <= 8 ms
- Input-to-output latency p95 <= 12 ms
- Jitter p95 <= 2 ms during steady-state mapping

### 6.2 Worker Control Plane

- gRPC unary control calls timeout after 750 ms by default
- Worker heartbeat interval: 500 ms
- Worker marked `DEGRADED` after 2 missed heartbeats
- Worker restart begins after 3 consecutive missed heartbeats
- Maximum restart frequency before escalation: 3 restart attempts within 60 s
- If restart ceiling is exceeded, worker state becomes `FAILED`

### 6.3 Queueing And Backpressure

- Capture-to-worker queue depth: maximum 3 frames in flight per worker
- Inference result queue depth: maximum 8 messages
- Inference result latency: p95 <= 16 ms (1 frame interval)
- Overflow policy for frame dispatch: drop oldest unconsumed frame and increment
  overflow counter
- Backpressure must never block the primary input-to-output path

### 6.4 Capture Stability

- 60 FPS baseline required on supported hardware
- 120 FPS validated path required for at least one supported v1 hardware path
- 240 FPS remains capability-based only
- A sustained drop means measured FPS below 90% of target for >= 3 continuous
  seconds or dropped frames > 2% over a rolling 5-second window

---

## 7) Execution Contracts

### 7.1 Shared Memory Ring Buffer

The shared memory frame ring buffer must define at minimum:

- ring slot count
- frame width and height
- pixel format enum
- stride in bytes
- timestamp in nanoseconds
- sequence number
- producer and consumer cursors
- overflow policy and overflow counter

Default v1 contract:

- ring slot count: 4
- default frame shape: 1920x1080
- supported v1 pixel labels: `BGR24`, `NV12`, `YUY2`, `MJPEG`, `RGB32`
- overflow policy: drop oldest unconsumed frame

### 7.2 Control Plane gRPC Surface

The minimum control-plane schema must cover:

- capture start
- capture stop
- worker heartbeat
- worker log forwarding
- plugin load result and load error
- diagnostics export request and response

Each control-plane operation must define timeout and retry posture in the proto
documentation and tests.

### 7.3 Runtime States

User-visible runtime states are:

- `RUNNING`
- `DEGRADED`
- `RECOVERING`
- `FAILED`
- `LOCKED`
- `GRACE`

These states must appear consistently across host logic, status HUD, logs, and
failure UX.

---

## 8) Signing, Trust, And Entitlements

### 8.1 Trust Baseline

All shipped native plugins and protected artifacts must use:

- Windows Authenticode
- SHA-256 digest
- RSA-3072 signing key
- publisher-chain validation to a pinned Aetherflow trust root

The host must block load or install when an artifact is:

- unsigned
- tampered
- expired
- revoked
- signed by an untrusted publisher

### 8.2 Premium Load Gating

Premium plugins may be present on disk while locked, but when locked the host
must:

- refuse process load
- refuse plugin registration
- refuse panel, device, or service exposure
- remove the plugin from activation selectors

Allowed entitlement states:

- `LOADED`: valid entitlement, normal operation
- `GRACE`: temporary load allowed with warning
- `LOCKED`: no load allowed

### 8.3 GRACE Warning Semantics

- HUD badge is always visible while in `GRACE`
- Toast is shown on first premium load per session
- Modal appears only when grace expires or renewal fails
- Grace expiry mid-session must unload only the affected premium feature and keep
  the host alive

---

## 9) Functional Requirements

### 9.1 Plugin System — P0

Plugin categories:

- input providers
- output providers
- capture providers
- display panels
- inference engines
- scripting engines
- Online Resources client
- environment manager
- admin dashboard

Each plugin must expose:

- `plugin_id`, `name`, `version`, `api_version`, `plugin_type`
- lifecycle methods
- structured capabilities
- `required_entitlements[]`
- `requires_drivers[]`
- `requires_worker`

### 9.2 Controller Core — P0

- Profile create, clone, export, import, and fast switch
- Per-button mapping
- Deadzones, curves, smoothing, sensitivity layers
- Translation across controller families and KBM ingestion
- Diagnostics for event rate, output rate, latency, and jitter

### 9.3 Output Virtualization — P0

- Driver-backed virtual controller output
- Optional device masking
- Guided install, repair, and disable flows
- Reversible actions only

### 9.4 Capture System — P0

#### OpenCV Capture

- Default capture source plugin for v1
- UI controls:
  - capture source dropdown
  - frame rate dropdown: 30, 60, 120, 240
  - resolution dropdown: 720p, 1080p, 1440p
- UI must show only supported combinations for the selected device
- UI must show reason text for unavailable combinations
- UI must show measured FPS, dropped frames, and jitter

#### Capture Guarantees

- 60 FPS baseline required on supported hardware
- 120 FPS validated path required in release evidence
- 240 FPS offered only where runtime capability matrix allows it
- UI copy must never imply unsupported high-FPS paths

#### Premium MF / DS Capture

- Locked plugins appear in catalog as premium locked
- Locked plugins do not register providers or panels
- Unlocked plugins add a format selector

#### OBS Capture

- Fixed configuration
- Start/stop only
- Measured FPS and stability metrics visible

### 9.5 Display Panels — P0

- CPU renderer: lowest latency, accurate FPS, fullscreen support
- GPU renderer: lower CPU load, potentially higher latency, may require restart
  on unload

### 9.6 Input Device Plugins — P0

- XInput-class controllers
- Modern PlayStation controllers
- Legacy PlayStation controllers where relevant
- Keyboard and mouse ingestion layer

### 9.7 Out-of-Process Workers — P0

- All Python scripts and vision processing run out of process
- Supervisor handles start, stop, restart, heartbeat, and escalation
- UI surfaces worker logs and health state
- Worker failure must not crash the host

### 9.8 Environment Management — P0

The environment manager must support create, repair, recreate, and delete.

Validation contract:

- required imports resolve
- dependency count is reported
- Python version is reported
- optional GPU probe returns one of `not-run`, `supported`, `unsupported`,
  `error` (probe timeout: 5s)

### 9.9 Online Resources — P0

Artifact types:

- scripts
- profiles
- models and weights
- environment bundles

Requirements:

- manifest includes SHA-256, size, version, and signature
- manifest trust chain pinned to the app trust root
- premium resources show required tier or add-on
- one-click install with logs and progress

Auth provider remains product-open, but implementation must support a
provider-agnostic OAuth interface.

### 9.10 Admin Dashboard — P0

- create users
- assign roles
- assign entitlements
- revoke sessions or devices
- audit admin actions

---

## 10) Failure UX And Recovery

### 10.1 Plugin Crash

Plugin crash behavior:

- unload the plugin
- keep the host and shell alive
- show status HUD `DEGRADED`
- show a toast naming the failed plugin
- expose a manual reload action
- expose copy-diagnostics action

### 10.2 Worker Unrecoverable Loop

Worker unrecoverable loop behavior:

- mark worker `FAILED`
- disable dependent plugin features
- keep host alive
- show blocking modal only for the affected feature surface
- keep unrelated plugins and the shell operational

### 10.3 Capture Backend Failure

If capture fails:

- stop capture cleanly
- preserve shell, profiles, and non-capture features
- show remediation guidance
- expose copy-diagnostics action

---

## 11) UX Requirements

- Dark theme with purple accents
- Always-visible status HUD for active plugins, measured FPS/jitter, worker
  health, and entitlement state
- Online Resources details modal must show metadata, install action, progress,
  logs, and final state
- Failure surfaces must distinguish degraded, recovering, and failed states

---

## 12) Packaging, Updates, And Diagnostics

- Self-contained runtime layout for Windows
- Dedicated updater with staged updates and rollback
- Diagnostics export must include:
  - plugin list and versions
  - env list and metadata
  - recent host and worker logs
  - system summary
  - overflow and restart counters

---

## 13) Success Metrics

| Metric                             | Target                                  | Verification Method                                            | Evidence Artifact                   |
| ---------------------------------- | --------------------------------------- | -------------------------------------------------------------- | ----------------------------------- |
| Install -> baseline mapping        | Median <= 5 min                         | Automated e2e test script                                      | `logs/onboarding_timing.json`       |
| Primary path latency               | median <= 8 ms, p95 <= 12 ms            | Integration latency suite                                      | `logs/latency_budget_report.json`   |
| Environment bundle installs        | >= 95% over 100 simulated installs      | `uv run pytest tests/test_bundle_installer.py --count=100`     | `logs/bundle_install_report.json`   |
| Host survivability on worker crash | >= 99.9% host remains alive             | `uv run pytest tests/stress/test_worker_crash_loop.py -n 1000` | `logs/survivability_report.json`    |
| Capture stability at 60 FPS        | >= 95% sessions without sustained drops | `uv run pytest tests/integration/test_capture_stability.py`    | `logs/capture_stability.json`       |
| Validated 120 FPS path             | at least 1 passing supported path       | `uv run pytest tests/integration/test_capture_120fps_path.py`  | `logs/capture_120fps_report.json`   |
| Premium plugin blocking            | 100% block rate without entitlement     | `uv run pytest tests/test_plugin_loader.cpp`                   | `logs/entitlement_gate_report.json` |
| Unsigned artifact execution        | 0 occurrences                           | `uv run pytest tests/test_security.py`                         | `logs/security_audit.json`          |

---

## 14) Open Items

- Final auth provider selection
- Final tier definitions and pricing
- Protected model package cryptosystem and revocation UX (deferred to v1.1 per §9.12)
- Remote-play inclusion in v1 vs v1.1 (scoped as P1 in §9.13; decision required before Phase 6)
- Final external bundle extension and branding

## 15) Deferred To v1.1

These features are fully specified in this document but are intentionally out of scope for v1 implementation. The agent must not implement them unless a separate approval is received.

- Protected model package cryptosystem and revocation UX (§9.12)
- Remote-play integrations, if not approved for v1 (§9.13)
- Online Resources publisher/developer mode (§9.14)
