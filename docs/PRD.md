# Product Requirements Document (PRD) — Aetherflow (Windows v1)

**Document Date:** March 8th, 2026  
**Status:** Draft v1.6 (Capture UX + premium plugin load gating update) **Platform (v1):** **Windows only** 🪟  
**UI Tech:** **Qt for Python (PySide6 / Qt for Python 6.9.x)**  
**Theme:** Dark UI with purple undertones 🟣  
**Runtime:** Native DLL plugins + out-of-process Python workers; **gRPC (control plane) + shared memory (data plane)**  
**Monetization:** Tiered entitlements; some plugins/resources are **Premium**  
**Core thesis:** Microkernel host where **everything is a plugin**

---

## 1) Executive Summary

Aetherflow is a high-performance controller adapter ecosystem for gaming. It provides low-latency input translation and output emulation, while enabling high-FPS “sensing” (capture + inference) and safe extensibility via out-of-process workers. The system is designed so features ship as **plugins** (capture backends, UI panels, input providers, inference engines, remote-play bridges, etc.), with optional **Premium** gating.

This revision adds specific plugin-driven capability requirements derived from the provided plugin feature overview (display/capture backends, input device support, remote-play integrations, 1000 Hz scripting VM characteristics, and an online resources system that can distribute single-file environment bundles and protected model packages).

## G3 Framework — Cognitive Anchor

### Guidelines (Project Context + Intent)

- **Core thesis:** Microkernel host where everything is a plugin. No exceptions.
- **Platform:** Windows only (v1). No cross-platform abstractions.
- **Tech stack:** C++20 (native plugins), Python 3.12 (workers + UI), PySide6 6.9.x (shell).
- **IPC:** gRPC control plane + shared memory data plane. No alternatives.
- **Monetization:** Tiered entitlements. Premium plugins ship locked, not absent.
- **Priority order when requirements conflict:** Host Stability > Security/Signing > Feature Completeness > Performance > UX Polish

### Guidance (Interpretive Logic)

- When a PRD section is ambiguous, default to the most restrictive interpretation.
- "Contract" items (ABI, proto, shared memory layout) are frozen after Phase 0. Any agent that modifies a frozen contract MUST log a breaking-change entry.
- TDD is not optional. Tests are written first, executed to prove failure, then implementation is written, then tests are re-executed to prove passage.
- File paths in PLAN are canonical. Do not rename or relocate without a traceability update.

### Guardrails (Hard Boundaries + Automated Gates)

- NEVER load a premium plugin DLL without a valid entitlement token. A grace-period token (GRACE state) is conditionally valid: loading is permitted but the user must be warned of imminent expiry.
- NEVER execute an unsigned artifact.
- NEVER modify `plugin_system.hpp` without a breaking-change log entry.
- NEVER bypass gRPC for worker-to-host communication.
- NEVER write to `src/plugins/*` — use `src/aetherflow/plugins/*`.
- ASK FIRST: changes to `capture.proto`, `shared_memory_layout.py`, billing/entitlement state machine semantics, auth provider selection.
- ALWAYS run `uv run ruff check && uv run pytest` before marking an item done.
- ALWAYS use Loguru for logging — no print statements.
- ALWAYS use Google-format docstrings on all public Python functions.
- ALWAYS include type hints on all Python function signatures.

---

## 2) Goals and Non-Goals

### 2.1 Goals ✅

- **Easy setup (mandatory):** install → sign-in → baseline mapping working quickly.
- **Deterministic I/O path:** input → mapping → output stays low-latency.
- **Capability-based capture:** 60–240 FPS where supported; UI never exposes unsupported modes.
- **Out-of-process vision/scripting:** safe, restartable, observable.
- **In-app uv environments:** create/manage/remove isolated envs with no terminal.
- **Online Resources:** install scripts/models/profiles/**environment bundles** with one click.
- **Premium gating:** ship premium plugins with installer but lock until entitled.

### 2.2 Non-Goals (v1) ❌

- macOS/Linux support
- In-app model training pipelines (inference only)
- Supporting unsigned third-party native plugins
- Anti-cheat bypass / covert cheating scenarios

---

## 3) Role-Based Behavioral Models

| Role | Access Scope | Entitlement Level | Key Behaviors |
| --- | --- | --- | --- |
| **Power Gamer** | Profile CRUD, mapping, fast-switch | Free/Pro | No admin, no billing, no env management |
| **Vision/ML Tinkerer** | Env create/delete, resource install, capture config | Pro/Vision | No billing admin, no user management |
| **Accessibility Modder** | Scripting VM, calibration tooling, automation primitives | Pro | No capture premium features unless entitled |
| **Admin/Operator** | Full entitlement + user management, audit log | Enterprise | Can revoke sessions, assign tiers, view all logs |

---

## 4) Architectural Principles (Hard Requirements)

### 4.1 Microkernel host

Host contains only:

- plugin loader/registry
- service container (logging/config/auth/telemetry)
- UI shell/router (panels are plugins)
- worker supervisor + IPC endpoints

Everything else ships as plugins.

### 4.2 Sensing vs Acting split

- **Sensing (PC):** capture, preview, metrics, inference (async).
- **Acting (output):** virtual controller output (driver-backed); optional future hardware-bridge output.

### 4.3 Asynchronous execution

- Primary IO loop must remain low-latency.
- Inference and heavy CV run off the main dispatch path with bounded queues/backpressure.

### 4.4 Frozen Contracts — DO NOT CHANGE

The following are frozen after Phase 0 completion. No agent may modify these without an explicit breaking-change log entry and human sign-off:

| File | Frozen After | Breaking Change Log Path |
| --- | --- | --- |
| `include/plugin_system.hpp` | Phase 0 | `docs/breaking-changes/abi.md` |
| `proto/capture.proto` | Phase 0 | `docs/breaking-changes/proto.md` |
| `src/aetherflow/core/shared_memory_layout.py` | Phase 0 | `docs/breaking-changes/shmem.md` |
| `src/aetherflow/core/entitlements.py` (state machine) | Phase 4 | `docs/breaking-changes/entitlements.md` |

Agents that detect a required change to a frozen file MUST:

1. Stop execution.
2. Report: "FROZEN CONTRACT MODIFICATION REQUIRED: `file` — `reason`."
3. Await human instruction before proceeding.

### 4.5 Agent Boundary Rules

**NEVER:**

- Load premium plugin DLLs without a valid entitlement token
- Execute unsigned artifacts (plugins, environment bundles, model packages)
- Write to `src/plugins/*` (use `src/aetherflow/plugins/*`)
- Bypass the gRPC control plane for worker-to-host communication
- Commit secrets, API keys, or tokens
- Use `print()` — use `loguru.logger` instead

**ASK FIRST:**

- Any modification to a frozen contract (see 4.4)
- Changes to entitlement state machine semantics
- Auth provider selection or changes
- Database schema changes
- Billing or pricing logic changes
- Remote-play v1 vs v1.1 scoping decisions

**ALWAYS:**

- Run `uv run ruff check && uv run pytest` before marking a work item done
- Write tests first (TDD) — prove failure before writing implementation
- Use Google-format docstrings on all public Python functions
- Use type hints on all Python function signatures
- Log breaking-change entries before modifying frozen contracts
- Document new gRPC endpoints in `docs/proto/`

---

## 5) Functional Requirements

## 5.1 Plugin System (Native DLLs) — P0

### 5.1.1 Plugin categories

- Input providers
- Output providers
- Capture providers
- Display/render panels
- Inference engines
- Scripting engines
- Remote-play integrations
- Online Resources client (catalog + install)
- Environment manager (uv)
- Admin dashboard
- Bridge plugins (optional future hardware)

### 5.1.2 Plugin contract (minimum)

Each plugin must expose:

- Identity: `plugin_id`, `name`, `version`, `api_version`, `plugin_type`
- Lifecycle: `Initialize(Services*)`, `Start(Profile*)`, `Stop()`, `Shutdown()`
- Capabilities: `GetCapabilities()` (structured, versioned)
- Policy: `required_entitlements[]`, `requires_drivers[]`, `requires_worker(bool)`

### 5.1.3 Plugin trust, signing, and premium load gating

- All shipped plugins must be **publisher-signed**.
- The host must verify **signature + ABI/api compatibility** before any load attempt.
- **Premium gating (hard rule):** premium plugins **must not be loadable** until the user completes a purchase and the entitlement check succeeds.
  - “Not loadable” means:
    - the DLL is not loaded into the process
    - the plugin cannot register UI panels, devices, or services
    - the plugin cannot be selected/activated in any dropdowns
- UX for locked premium plugins:
  - visible in the plugin catalog as **Premium (Locked)** with required tier/add-on
  - attempts to activate show a purchase CTA and a brief capability summary
  - after purchase, an entitlement refresh enables loading **without reinstall** (restart optional if the plugin requires it)

### 5.1.3 Trust, signing, and gating

- All shipped plugins must be publisher-signed.
- Premium plugins may ship with the installer, but they are **not loadable** until entitlement checks succeed.
- Host blocks unsigned/tampered plugins and shows actionable errors.

### 5.1.4 On-demand plugin loading

- User may load additional plugin DLLs at runtime from an approved directory if signed and policy-allowed.
- If a selected DLL is **Premium** and the user is not entitled, the host must block loading and route the user to the purchase flow.

### 5.1.5 Critical State Machines (TAR Format)

#### Entitlement / Premium Plugin Gating

`[ENT-TAR-01] -> [PRD-§5.1.3, §7]`

| Trigger | Condition | Action | Result State |
| --- | --- | --- | --- |
| `Host::LoadPlugin(plugin_id)` called | Plugin is NOT premium | Load normally | `LOADED` |
| `Host::LoadPlugin(plugin_id)` called | Plugin is premium, entitlement valid | Load plugin | `LOADED` |
| `Host::LoadPlugin(plugin_id)` called | Plugin is premium, entitlement invalid | Block load, show purchase CTA | `LOCKED` |
| `Host::LoadPlugin(plugin_id)` called | Plugin is premium, grace period active | Load plugin, warn user of expiry | `GRACE` |
| `Host::LoadPlugin(plugin_id)` called | Plugin is premium, grace period expired | Block load, show renewal CTA | `LOCKED` |
| Purchase completed | Entitlement token received | Refresh entitlement cache | `ELIGIBLE` |
| Entitlement refresh | Token valid | Enable plugin without reinstall | `LOADED` |
| TTL expires (offline) | Grace period active | Warn user, maintain access | `GRACE` |
| TTL expires (offline) | Grace period expired | Lock premium features | `LOCKED` |

GRACE state: entitlement is conditionally valid; premium plugins may load with expiry warning. LOCKED state: entitlement invalid; premium load blocked.

#### Python Worker Lifecycle

`[WRK-TAR-01] -> [PRD-§5.9]`

| Trigger | Condition | Action | Result State |
| --- | --- | --- | --- |
| Worker start requested | Env valid, supervisor running | Spawn subprocess, start heartbeat | `STARTING` |
| Heartbeat received | Within timeout | Update health state | `RUNNING` |
| Heartbeat missed | Within retry window | Increment miss counter | `DEGRADED` |
| Heartbeat missed | Retry window exceeded | Kill + restart with backoff | `RECOVERING` |
| Worker crash detected | Any | Log crash, trigger restart | `RECOVERING` |
| Restart succeeds | — | Resume heartbeat monitoring | `RUNNING` |
| Restart fails 3x | — | Mark worker FAILED, alert UI | `FAILED` |

#### Environment Bundle Install

`[ENV-TAR-01] -> [PRD-§5.10.2]`

| Trigger | Condition | Action | Result State |
| --- | --- | --- | --- |
| Install initiated | SHA-256 valid, signature valid | Extract bundle, stream logs | `INSTALLING` |
| Install initiated | SHA-256 mismatch | Reject, show error | `FAILED` |
| `uv sync` completes | Exit 0 | Validate imports | `VERIFYING` |
| Validation passes | All imports resolve | Mark env ready | `READY` |
| Validation fails | Import error | Show failed deps, offer repair | `FAILED` |

---

## 5.2 Controller Adapter Core — P0

- Profile system: create/clone/export/import; fast switching.
- Mapping: per-button mapping; deadzones/curves/smoothing; sensitivity layers.
- Translation: controller→controller; optional KBM ingestion; script-driven transforms.
- Diagnostics: event rate, output rate, latency/jitter sampling.

---

## 5.3 Windows Output Virtualization + Device Masking — P0

- Virtual controller emulation (driver-backed).
- Optional device masking/hiding to prevent double input.
- UX:
  - driver status panel
  - guided install/repair flows
  - explicit explanations and reversible actions

---

## 5.4 Capture System (60–240 FPS) — P0

### 5.4.1 Default capture plugin: OpenCV Capture (mandatory)

**Default behavior (v1):** The default capture source plugin is **OpenCV Capture**.

**UI contract (v1):** OpenCV Capture exposes exactly these controls:

1. **Capture source** (dropdown)
   - User selects a _capture device endpoint_ (e.g., capture card, OBS Virtual Camera, other camera endpoints).
2. **Settings** (tab)
   - **Frame rate** dropdown: **30, 60, 120, 240**
   - **Resolution** dropdown:
     - **720p** (1280×720)
     - **1080p** (1920×1080)
     - **1440p** (2560×1440)

**Important constraint:** Not all devices can achieve all target FPS/resolution combinations. The UI must:

- only present supported combinations as selectable (others disabled or hidden)
- show a clear reason when a choice is unavailable (bandwidth/connection/backend limitations)
- show **measured FPS** + dropped frames/jitter after start

**Device examples (non-exhaustive; for UX expectations only):**

- Elgato “4K X” class (high performance; high-bandwidth USB-C class)
- Elgato “4K S” class (high performance/value; USB 3.0 class)
- Elgato “4K Pro” class (PCIe; **not** MK.2 variant per your constraint)
- Elgato “HD60 X / S / S+ / Pro / 4K60 Pro MK.2” classes
- AverMedia “Live Gamer HD 2 Ultra” class
- OBS Virtual Camera endpoints

> **Implementation requirement:** The Capture source dropdown must be populated from runtime device enumeration and include stable device identifiers so profiles remain valid across reboots (best-effort with friendly name + unique ID).

### 5.4.2 Capability-based mode selection (mandatory)

Capture plugins must advertise a **mode matrix** at runtime. The UI must only present modes that the active plugin reports as supported for the **currently selected device**.

**Mode descriptor fields (minimum):**

- `capture_width`, `capture_height`, `capture_fps`
- `pixel_format_in` (e.g., NV12, YUY2, MJPEG, RGB32)
- `pixel_format_out` (e.g., BGR) or a `conversion_pipeline` label
- `zero_copy_supported` (bool)
- `hdr_supported` (bool)
- `passthrough_supported_modes[]` (optional separate list)
- `notes` (driver/SDK constraints, bandwidth assumptions)

### 5.4.3 Premium capture plugins: MF Capture / DS Capture (not loadable until purchase)

**Premium gating (hard rule):** **MF Capture** and **DS Capture** are premium plugins and **must not be loadable** until a purchase is completed and entitlements validate.

- While locked:
  - the plugins appear in the plugin catalog as **Premium (Locked)**
  - they do **not** appear as selectable capture providers
  - they do **not** register UI panels or device endpoints
- After purchase:
  - the plugins become loadable and can be selected as the active capture provider
  - entitlement refresh should unlock without reinstall (restart optional if required by backend)

**When enabled (unlocked), MF/DS capture UI contract (v1):**

- Same structure as OpenCV Capture:
  - Capture source dropdown
  - Settings tab: FPS + Resolution
- Additional control:
  - **Format** dropdown (conversion/bandwidth/latency tuning)

**Format dropdown options (v1):**

- **NV12 → BGR** — best for **120+ FPS on USB 3.0** (lower bandwidth)
- **BGR Direct** — zero conversion; requires **high bandwidth** (PCIe / USB 3.2 class)
- **YUY2 → BGR** — high quality 4:2:2; common default
- **MJPEG → BGR** — for USB 2.0 or constrained bandwidth; **adds latency**
- **RGB32 → BGR** — professional PCIe cards only; full 32-bit color

### 5.4.4 OBS Capture plugin (fixed behavior)

OBS Capture does **not** expose dropdown menus. It is a fixed-configuration capture plugin:

- starts/stops capture
- surfaces measured FPS and stability metrics
- (optionally) provides only a status indicator and a “Configure in OBS” helper affordance

### 5.4.5 Metrics and stability UX (mandatory)

For all capture plugins:

- Always show:
  - target mode vs measured FPS
  - dropped frames
  - jitter
- If stability drops below threshold:
  - recommend supported fallback modes (one-click apply)
  - provide a “copy diagnostics” action for support

## 5.5 Display / Render Panels — P0 (as plugins)

Aetherflow must provide at least two rendering strategies (as separate UI panel plugins), presented to users as “render modes” rather than exposing implementation names:

- **CPU renderer:** lowest latency, accurate FPS, supports fullscreen; includes resolution/performance render modes.
- **GPU renderer:** reduces CPU load and can support adjustable presentation FPS, but may have slightly higher latency; may require restart when unloaded.

---

## 5.6 Input Device Plugins — P0

Minimum device categories (plugin-based):

- XInput-class controllers (very low latency; should function without mandatory masking).
- Direct support for modern PlayStation controllers (no third-party driver dependency).
- Direct support for legacy PlayStation controllers where relevant.
- Keyboard & mouse ingestion layer as a foundation for future KBM plugins.

---

## 5.7 Remote-Play Integrations — P1 (recommended, but spec’d now)

Remote-play integrations are plugins that:

- connect via platform APIs
- support secure login flows
- provide event-driven, low-latency input/capture pipelines
- maintain low CPU usage where possible

> v1 decision: If remote-play ships in v1, it must still respect the core: deterministic I/O path, capability matrices, and the same worker supervision model.

---

## 5.8 Scripting + Inference Engines — P0/P1 (depending on SKU)

### 5.8.1 High-frequency scripting VM (P1 recommended)

Provide a local scripting engine capable of high-frequency execution (e.g., 1000 Hz class), using a secure bytecode format and designed to integrate with remote-play and mid-frame injection patterns.

**Key requirement:** scripting execution must not block the primary I/O loop; it should run in a bounded worker thread or out-of-process if safety demands.

### 5.8.2 Native inference engine (P1 recommended)

Provide a C++ inference engine plugin that can run ONNX-style pipelines asynchronously and optionally produce an optimized engine artifact (“built” model), with support for protected/encrypted model packages. Aetherflow must not reuse third-party naming schemes for these packages.

---

## 5.9 Out-of-Process Python Workers — P0

- All Python scripts/vision run out-of-process.
- IPC:
  - gRPC control plane (commands/health/logs/results)
  - shared memory frame ring buffer (data plane)
- Supervisor:
  - start/stop/restart
  - heartbeat monitoring
  - crash recovery with backoff
- UI must surface worker logs + health state.

---

## 5.10 uv Environments in UI — P0

### 5.10.1 Environment manager UX

- Create / Repair / Recreate / Delete (with confirmation)
- Show:
  - Python version
  - dependency count
  - disk usage
  - last updated
  - validation status (imports, optional GPU check)

### 5.10.2 Single-file environment bundles — P0

Online Resources must support a single-file environment bundle format that:

- defines Python version target
- defines dependency set (pinned/locked)
- supports multiple variants (CPU vs CUDA)
- supports update by publishing a new bundle version
- installs with **one click** and streams install logs in UI

**Naming requirement:** do not adopt external names (e.g., “.henv”). Aetherflow must define its own bundle term and extension (TBD), while supporting the same workflow concept.

**Compatibility note:** environment bundles are not required to be compatible with other ecosystems/tools.

---

## 5.11 Online Resources (CDN + Signed Manifest) — P0

### 5.11.1 Artifact types

- Scripts
- Profiles
- Models/weights (including protected/premium variants)
- Environment bundles

### 5.11.2 Integrity and trust

- All artifacts require SHA-256 + size + version.
- Manifest is signed and pinned to an app trust root.
- Premium artifacts/resources show lock state and required tier/add-on.

### 5.11.3 Publishing workflow (P1)

- Role-gated “developer/publisher mode” for uploading scripts and environment bundles.
- Support private resources and DRM-style locking for controlled distribution.

### 5.11.4 Authentication for Online Resources

Auth provider remains undecided globally, but the Online Resources system must support OAuth-style providers. A “social login” provider can be used for the resources ecosystem if selected.

---

## 5.12 Admin Dashboard — P0

- Create users
- Assign roles
- Assign entitlements (tiers + add-ons)
- Revoke sessions/devices
- Audit log for admin actions

---

## 6) UX Requirements

- Dark theme with purple accents.
- Always-visible status HUD:
  - active input/output/capture/display plugins
  - measured FPS/jitter
  - worker health
  - entitlement state (when relevant)
- Online Resources “details modal” must provide:
  - artifact metadata
  - one-click install
  - streamed install logs + progress
  - clear success/failure states

---

## 7) Tiers and Entitlements

- Tiers (example): Free / Pro / Vision / Enterprise
- Add-ons: capture backend packs, inference packs, protected model packs
- Offline grace:
  - cache entitlements with TTL (7–30 days recommended)
  - after TTL expiry offline: premium locks; base features remain usable

---

## 8) Packaging, Updates, Diagnostics (Windows)

- Self-contained runtime layout (exe + lib + plugins + styles + translations + content folders).
- Dedicated updater with staged updates and rollback.
- Diagnostics export includes:
  - plugin list + versions
  - env list + metadata
  - recent logs (host + workers)
  - basic system summary

---

## 9) Success Metrics (Machine-Verifiable)

| Metric | Target | Verification Method | Evidence Artifact |
| --- | --- | --- | --- |
| Install -> working baseline mapping | Median <= 5 min on clean Win11 VM | Automated e2e test script | `logs/onboarding_timing.json` |
| Environment bundle install success rate | >= 95% over 100 simulated installs | `uv run pytest tests/test_bundle_installer.py --count=100` | `logs/bundle_install_report.json` |
| Host survivability on worker crash | >= 99.9% (host stays running) | `uv run pytest tests/stress/test_worker_crash_loop.py -n 1000` | `logs/survivability_report.json` |
| Capture stability at 60 FPS baseline | >= 95% sessions without sustained drops | `uv run pytest tests/integration/test_capture_stability.py` | `logs/capture_stability.json` |
| Premium plugin blocked without entitlement | 100% block rate | `uv run pytest tests/test_plugin_loader.cpp` | `logs/entitlement_gate_report.json` |
| Unsigned artifact execution | 0 occurrences | `uv run pytest tests/test_security.py` | `logs/security_audit.json` |

---

## 10) Open Items

- Auth provider selection (global)
- Final tier definitions and pricing
- Protected model package cryptosystem + revocation UX details
- Remote-play inclusion in v1 vs v1.1
- Aetherflow-owned environment bundle extension and schema (TBD)
