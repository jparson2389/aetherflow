# Aetherflow Windows v1 P0 Implementation Plan

## Summary

Grounded in `docs/PRD.md`, `AGENTS.md`, and `docs/architecture/system_overview.md`.

Source anchors verified in-repo on March 8, 2026:

- `AGENTS.md`
- `docs/architecture/system_overview.md`

---

Rules for this plan:

- Canonical product/package name is `Aetherflow`.
- Python lives under `src/aetherflow/`; C++ lives only under `host/` and
  `include/`.
- Scope is Windows v1 `P0` only. Deferred: `PRD-§9.12` protected-model
  cryptosystem work, `PRD-§9.13` remote-play, and `PRD-§9.14` Online
  Resources publisher or developer mode.
- Frozen contracts after Phase 0: `include/plugin_system.hpp`,
  `proto/capture.proto`, `src/aetherflow/core/shared_memory_layout.py`.
- Entitlement state machine freezes after Phase 4:
  `src/aetherflow/core/entitlements.py`.
- Supervision authority is host-owned: `Aetherflow.exe` is the supervisor of
  record, and Python surfaces render or relay authoritative host state rather
  than acting as the supervisor of record.
- host-owned worker supervision remains a hard architecture boundary for
  lifecycle, restart-budget, heartbeat, and escalation authority.
- Python-side adapters only where needed for shell clients.
- Product-delivery work is the priority. Treat `tools/` as development-only support infrastructure unless the work item is explicitly about packaging, validation, or repo maintenance.
- Mandatory validation for completed work remains `uv run ruff check .` and
  `uv run pytest`.
- TDD is required on every work item.

## Completion Policy (All Work Items)

To mark any work item `done`, it must satisfy _all_ of the following:

- **Behavior evidence:** real runtime behavior exists, not just static data or
  model definitions.
- **Test depth:** tests must exercise behavior, not only constants or field
  presence.
- **Artifacts:** when required, evidence files/logs are generated and reviewed.
- **Disallowed evidence:** any of the following _alone_ is insufficient:
  - file presence or non-empty stubs
  - dataclasses or model-only wrappers
  - hard-coded "valid" signatures or fixed tables
  - tests that only assert constant values

When unsure, mark the item **partial** or **scaffolded** and document gaps.

---

## Atomic Recovery Protocol (ARP)

If any validation command exits non-zero:

1. **CAPTURE:** `git diff > _recovery/failed_state_<timestamp>.patch`
2. **ANALYZE:** `uv run ruff check <failing_file>` and
   `uv run pytest <failing_test> -vv`
3. **REPORT:** "Validation failed because: `<reason>`. Affected file: `<path>`."
4. **FIX:** One minimal fix attempt only.
5. **REVERT:** If fix fails, `git checkout -- <files>`, report BLOCKED.

Every work item that has a validation command implicitly triggers ARP on
non-zero exit. Agents must not skip to the next retry without executing
steps 1–3 first.

---

## Assumptions And Sign-Off Gates

- `[ASM-01]` `proto/` remains the authoritative proto source; generated Python
  lands under `src/aetherflow/proto/`.
- `[ASM-02]` Auth provider selection remains product-open until before
  `AF-05-01`. Fallback: provider-agnostic OAuth interface plus disabled
  `MockOAuthProvider`.
- `[ASM-03]` Bundle extension naming remains product-open until before
  `AF-04-02`. Fallback: signed archive with internal `bundle.json` metadata.
- `[ASM-04]` Protected model cryptosystem stays out of v1 implementation unless
  separately approved.
- `[ASM-05]` Windows-hosted `uv` execution must be verified during Phase 0
  before contract freeze is treated as complete.
- `[ASM-06]` **Sign-Off SLA**: If human sign-off is requested for a frozen contract change or ambiguous requirement and no response is received within 24 hours, the agent must proceed with the documented fallback behavior to avoid blocking the critical path.

---

## Public Interfaces / Contracts

- `include/plugin_system.hpp`: native plugin trust, runtime state, and gating
  ABI.
- `proto/capture.proto`: normative control-plane contract for capture, worker
  heartbeats, logs, diagnostics export, and plugin load results.
- `src/aetherflow/core/shared_memory_layout.py`: ring-buffer metadata, pixel
  formats, stride semantics, and overflow policy.
- `src/aetherflow/core/entitlements.py`: `LOADED`, `GRACE`, `LOCKED` semantics.
- `host/` plus `include/`: supervisor-of-record for plugin lifecycle, worker
  start or stop, restart budgets, heartbeat handling, and escalation.
- `docs/PRD.md`: runtime budgets, state precedence, failure UX, and validated
  capture guarantees.

---

## Requirement Ledger

line-grow note: this ledger stays wide so requirement IDs and verification
columns remain readable without breaking each row into prose.

<!-- markdownlint-disable MD060 -->

| ID       | PRD Ref                        | Type                   | Summary                                                       | Dependencies                 | Verification                        |
| -------- | ------------------------------ | ---------------------- | ------------------------------------------------------------- | ---------------------------- | ----------------------------------- |
| `REQ-01` | `§5`                           | Constraint             | Windows-only microkernel host and frozen contracts            | none                         | contract and docs tests             |
| `REQ-02` | `§6`, `§7`, `§8`               | Security               | Numeric budgets, trust baseline, premium gating               | `REQ-01`                     | contract and policy tests           |
| `REQ-03` | `§9.1`, `§9.9`                 | Functional             | Signed plugin and resource loading with explicit trust checks | `REQ-02`                     | loader and security tests           |
| `REQ-04` | `§9.2`, `§9.6`                 | Functional             | Profiles, mapping, translation, input devices                 | `REQ-01`                     | profile and mapping tests           |
| `REQ-05` | `§9.3`, `§10.1`                | Functional/UX          | Virtual output, masking, host-safe plugin failure handling    | `REQ-04`                     | output and host survivability tests |
| `REQ-06` | `§9.4`, `§10.3`                | Functional/Performance | Capture 60 baseline, 120 validated path, capability-bound 240 | `REQ-02`, `REQ-03`           | capture compliance tests            |
| `REQ-07` | `§9.5`, `§11`                  | UX                     | CPU/GPU render modes and always-visible status HUD            | `REQ-03`, `REQ-06`           | UI tests                            |
| `REQ-08` | `§9.7`, `§10.2`                | Functional/Ops         | Worker supervision, escalation ceilings, failure UX           | `REQ-02`                     | worker stress tests                 |
| `REQ-09` | `§9.8`, `§9.9`                 | Functional             | Environment management and bundle validation                  | `REQ-08`                     | env and bundle tests                |
| `REQ-10` | `§9.10`, `§9.11`, `§12`, `§13` | Operations             | Admin, diagnostics, packaging, evidence artifacts             | `REQ-03`, `REQ-08`, `REQ-09` | integration and e2e tests           |

<!-- markdownlint-enable MD060 -->

---

## Phase 0 - Canonical Identity And Execution Contracts

- [x] `AF-00-01` Canonicalize repo identity and self-contained docs.
  > **PRD Refs:** `§1`, `§2`, `REQ-01`
  > **Role:** `core-runtime`
  > **Lifecycle:** `retired`
  > **Preconditions:** none
  > **Target File:** `docs/PRD.md`
  > **Target File:** `README.md`
  > **Target File:** `AGENTS.md`
  > **Target File:** `tests/contracts/test_canonical_identity.py`
  > **Target File:** `tests/contracts/test_prd_execution_readiness.py`
  > **Behavior:** remove stale aliases, keep PRD self-contained, and enforce canonical Python/C++ boundaries.
  > **Validation:** `uv run pytest tests/contracts/test_canonical_identity.py::test_canonical_package_root_is_aetherflow tests/contracts/test_canonical_identity.py::test_project_docs_reference_aetherflow_canonical_paths tests/contracts/test_prd_execution_readiness.py::test_prd_is_self_contained_and_citation_free`
  > **Evidence:** docs are citation-free and path-correct.
  > **Completion Gates:**
  >
  > - PRD and README paths are canonical and citation-free.
  > - Contract tests validate doc content and canonical package root.
  > - No placeholder or alias references remain in docs.
  >   **ARP Trigger:** if any canonical path conflicts with active repo structure, stop and capture the conflict.
- [x] `AF-00-02a` Verify Windows toolchain and `uv` environment.
  > **PRD Refs:** `§5.3`, `REQ-01`
  > **Role:** `core-runtime`
  > **Feature-Class:** `boundary`
  > **Entry-Point:** `verify-env.ps1`
  > **Acceptance Criteria:**
  >
  > - AC1: Environment verification detects required Windows toolchain prerequisites.
  >   **Required-Proof-Types:** `contract`
  >   **Evidence-Pack:** `docs/evidence/AF-00-02a.md`
  >   **App-Testable:** `false`
  >   **Required-Failure-Modes:** `missing toolchain detected`
  >   **Preconditions:** `AF-00-01`
  >   **Target File:** `scripts/verify-env.ps1`
  >   **Target File:** `tests/contracts/test_env_readiness.py`
  >   **Behavior:** verify `uv`, `powershell`, and `cl.exe` (MSVC) are available and functional.
  >   **Validation:** `uv run pytest tests/contracts/test_env_readiness.py`
  >   **Evidence:** environment report generated.
  >   **Completion Gates:**
  > - `scripts/verify-env.ps1` generates a report with tool availability.
  > - Contract test passes and report is present in `logs/`.
  > - No manual or mocked outputs used.
  >   **ARP Trigger:** if toolchain is missing, halt execution until resolved.
- [x] `AF-00-02b` Establish native boundary and build harness.
  > **PRD Refs:** `§5.3`, `REQ-01`
  > **Role:** `core-runtime`
  > **Feature-Class:** `boundary`
  > **Entry-Point:** `build-native.ps1`
  > **Acceptance Criteria:**
  >
  > - AC1: Build script produces a working native harness artifact.
  > - AC2: Native/Python boundary is enforced.
  >   **Required-Proof-Types:** `contract`
  >   **Evidence-Pack:** `docs/evidence/AF-00-02b.md`
  >   **App-Testable:** `false`
  >   **Required-Failure-Modes:** `native boundary violation rejected`
  >   **Preconditions:** `AF-00-02a`
  >   **Target File:** `host/`
  >   **Target File:** `include/`
  >   **Target File:** `scripts/build-native.ps1`
  >   **Target File:** `tests/contracts/test_native_harness.py`
  >   **Behavior:** scaffold `host/` and `include/` structure, create build script, and verify compilation of a minimal dummy target.
  >   **Validation:** `powershell -ExecutionPolicy Bypass -File scripts/build-native.ps1`
  >   **Evidence:** build artifacts present in `build/`.
  >   **Completion Gates:**
  > - Build script produces `build/native_harness.exe`.
  > - Contract test verifies build success without manual steps.
  > - Native boundary is enforced (no C++ in `src/`).
  >   **ARP Trigger:** if build fails, capture compiler output and stop.
- [x] `AF-00-03` Publish control-plane proto surface and shared-memory ring semantics.
  > **PRD Refs:** `§6`, `§7`, `REQ-01`, `REQ-02`, `REQ-08`
  > **Role:** `runtime-services`
  > **Feature-Class:** `boundary`
  > **Entry-Point:** `capture control contract`
  > **Acceptance Criteria:**
  >
  > - AC1: Control-plane proto surface matches PRD contract.
  > - AC2: Ring buffer semantics are published.
  >   **Required-Proof-Types:** `contract`
  >   **Evidence-Pack:** `docs/evidence/AF-00-03.md`
  >   **App-Testable:** `false`
  >   **Required-Failure-Modes:** `missing control-plane message rejected`
  >   **Preconditions:** `AF-00-02b`
  >   **Target File:** `proto/capture.proto`
  >   **Target File:** `src/aetherflow/core/shared_memory_layout.py`
  >   **Target File:** `docs/proto/capture.md`
  >   **Target File:** `tests/contracts/test_execution_contracts.py`
  >   **Behavior:** publish the normative gRPC message surface, timeout/retry expectations, ring metadata, pixel labels, and overflow policy.
  >   **Validation:** `uv run pytest tests/contracts/test_execution_contracts.py -k "proto or overflow"`
  >   **Evidence:** proto and shmem contracts match PRD execution semantics.
  >   **Completion Gates:**
  > - Proto and shared-memory fields match PRD contract semantics.
  > - Contract tests verify ring metadata and control-plane messages.
  > - Docs cover timeout and retry posture per RPC.
  >   **ARP Trigger:** if control-plane or ring semantics remain ambiguous, do not freeze them.
- [x] `AF-00-04` Publish signing and runtime-state ABI, then freeze contracts.
  > **PRD Refs:** `§5.3`, `§7`, `§8`, `REQ-02`, `REQ-03`
  > **Role:** `trust-security`
  > **Feature-Class:** `boundary`
  > **Entry-Point:** `plugin abi mirror`
  > **Acceptance Criteria:**
  >
  > - AC1: Plugin ABI and signing semantics are frozen and documented.
  > - AC2: Breaking-change docs are present.
  >   **Required-Proof-Types:** `contract`
  >   **Evidence-Pack:** `docs/evidence/AF-00-04.md`
  >   **App-Testable:** `false`
  >   **Required-Failure-Modes:** `missing runtime state rejected`
  >   **Preconditions:** `AF-00-03`
  >   **Target File:** `include/plugin_system.hpp`
  >   **Target File:** `docs/breaking-changes/abi.md`
  >   **Target File:** `docs/breaking-changes/proto.md`
  >   **Target File:** `docs/breaking-changes/shmem.md`
  >   **Target File:** `tests/contracts/test_execution_contracts.py`
  >   **Target File:** `tests/contracts/test_frozen_contracts.py`
  >   **Behavior:** publish Authenticode/RSA-3072 trust semantics, plugin runtime states, and freeze ABI/proto/shmem in one checkpoint.
  >   **Validation:** `uv run pytest tests/contracts/test_execution_contracts.py tests/contracts/test_frozen_contracts.py`
  >   **Evidence:** trust and state semantics are documented and frozen together.
  >   **Completion Gates:**
  > - ABI and breaking-change logs are present and non-placeholder.
  > - Contract tests verify trust/state symbols and freeze logs.
  > - No frozen-contract change without explicit sign-off entry.
  >   **ARP Trigger:** if trust policy or runtime states are still in flux, stop instead of publishing the freeze.
- [x] `AF-00-05` Publish bounded sign-off packets and failure-UX state model.
  > **PRD Refs:** `§7.4`, `§8.3`, `§10`, `§14`, `REQ-02`, `REQ-08`, `REQ-09`
  > **Role:** `platform-entitlements`
  > **Feature-Class:** `workflow`
  > **Entry-Point:** `sign-off packets`
  > **Acceptance Criteria:**
  >
  > - AC1: Sign-off packets encode deadlines and fallback rules.
  > - AC2: Plan readiness tests confirm presence.
  >   **Required-Proof-Types:** `contract`
  >   **Evidence-Pack:** `docs/evidence/AF-00-05.md`
  >   **App-Testable:** `false`
  >   **Required-Failure-Modes:** `missing fallback guidance rejected`
  >   **Preconditions:** `AF-00-04`
  >   **Target File:** `docs/sign-offs/auth-provider.md`
  >   **Target File:** `docs/sign-offs/bundle-format.md`
  >   **Target File:** `tests/contracts/test_prd_execution_readiness.py`
  >   **Behavior:** encode auth/bundle deadlines, fallbacks, and the host/plugin/worker degraded-state model so agents do not stall.
  >   **Validation:** `uv run pytest tests/contracts/test_prd_execution_readiness.py -k plan`
  >   **Evidence:** unresolved product decisions have explicit fallbacks and phase gates.
  >   **Completion Gates:**
  > - Sign-off docs include fallback rules and SLA language.
  > - Readiness tests confirm sign-off docs are present and referenced.
  > - No placeholder or TBD sign-off content.
  >   **ARP Trigger:** if a sign-off packet lacks fallback behavior, downstream work remains blocked.

### Phase 0 Exit Criteria

```text
uv run ruff check .
uv run pytest tests/contracts
powershell -ExecutionPolicy Bypass -File scripts/build-native.ps1
```

---

## Phase 1 - Trust, Entitlements, And Shell Resilience

- [x] `AF-01-01` Implement trust verification and plugin/resource catalog policy.
  > **PRD Refs:** `§8.1`, `§9.1`, `§9.9`, `REQ-02`, `REQ-03`
  > **Role:** `trust-security`
  > **Feature-Class:** `service`
  > **Entry-Point:** `signed plugin loading`
  > **Acceptance Criteria:**
  >
  > - AC1: Unsigned plugins are blocked before activation.
  > - AC2: Revoked/tampered plugins are rejected.
  >   **Required-Proof-Types:** `integration`
  >   **Evidence-Pack:** `docs/evidence/AF-01-01.md`
  >   **App-Testable:** `false`
  >   **Required-Failure-Modes:** `unsigned plugin blocked`
  >   **Preconditions:** `AF-00-04`
  >   **Target File:** `src/aetherflow/plugins/trust.py`
  >   **Target File:** `src/aetherflow/plugins/registry.py`
  >   **Target File:** `src/aetherflow/plugins/catalog.py`
  >   **Target File:** `tests/unit/test_plugin_registry.py`
  >   **Target File:** `tests/integration/test_signed_plugin_loading.py`
  >   **Target File:** `tests/test_security.py`
  >   **Behavior:** enforce Authenticode-rooted trust semantics and block unsigned/tampered/untrusted content before load or install.
  >   **Validation:** `uv run pytest tests/unit/test_plugin_registry.py tests/integration/test_signed_plugin_loading.py tests/test_security.py`
  >   **Evidence:** load/install refusal occurs before registration or activation.
  >   **Completion Gates:**
  > - Trust verification is not hard-coded and validates real inputs.
  > - Tests cover unsigned, tampered, revoked, and untrusted chains.
  > - Catalog and registry enforce trust before activation.
  >   **ARP Trigger:** any reachable unsigned path blocks the phase.
- [x] `AF-01-02` Implement entitlement runtime states and shell-safe degradation model.
  > **PRD Refs:** `§8.2`, `§8.3`, `§10.1`, `REQ-02`, `REQ-07`
  > **Role:** `platform-entitlements`
  > **Feature-Class:** `ui`
  > **Entry-Point:** `status hud`
  > **Acceptance Criteria:**
  >
  > - AC1: LOCKED state blocks plugin activation.
  > - AC2: Status HUD reflects degraded state.
  > - AC3: Shell survives plugin failure.
  >   **Required-Proof-Types:** `integration`
  >   **Evidence-Pack:** `docs/evidence/AF-01-02.md`
  >   **App-Testable:** `true`
  >   **App-Surface:** `status-hud`
  >   **Required-Failure-Modes:** `unauthorized navigation blocked`
  >   **Developer-Alert-Message:** `Entitlement state degraded — check plugin trust and license status`
  >   **Preconditions:** `AF-01-01`
  >   **Target File:** `src/aetherflow/core/entitlements.py`
  >   **Target File:** `src/aetherflow/ui/shell.py`
  >   **Target File:** `src/aetherflow/ui/router.py`
  >   **Target File:** `src/aetherflow/ui/status_hud.py`
  >   **Target File:** `tests/unit/test_entitlements.py`
  >   **Target File:** `tests/integration/test_plugin_catalog_locking.py`
  >   **Target File:** `tests/ui/test_status_hud.py`
  >   **Behavior:** implement `LOCKED`, `GRACE`, `DEGRADED`, `FAILED`, and HUD semantics without allowing plugin faults to take down the shell.
  >   **Validation:** `uv run pytest tests/unit/test_entitlements.py tests/integration/test_plugin_catalog_locking.py tests/ui/test_status_hud.py`
  >   **Evidence:** shell remains alive when plugins degrade or unload.
  >   **Completion Gates:**
  > - Entitlement state drives catalog, HUD, and failure UX behavior.
  > - Tests cover GRACE expiry, LOCKED gating, and degraded UX states.
  > - Host remains responsive under plugin failure paths.
  >   **ARP Trigger:** if plugin failure can terminate the shell, stop and capture the crash path.

### Phase 1 Exit Criteria

```text
uv run ruff check .
uv run pytest tests/unit/test_plugin_registry.py tests/unit/test_entitlements.py tests/integration/test_signed_plugin_loading.py tests/integration/test_plugin_catalog_locking.py tests/ui/test_status_hud.py tests/test_security.py
```

---

## Phase 2 - Controller Core, Input Layer, And Output Virtualization

- [x] `AF-02-01` Deliver profiles, mapping, translation, diagnostics, and input plugins.
  > **PRD Refs:** `§6.1`, `§9.2`, `§9.6`, `REQ-04`
  > **Role:** `native-io-capture`
  > **Feature-Class:** `service`
  > **Entry-Point:** `profile crud pipeline`
  > **Acceptance Criteria:**
  >
  > - AC1: Profile CRUD operates deterministically.
  > - AC2: Mapping pipeline includes latency telemetry.
  >   **Required-Proof-Types:** `integration`
  >   **Evidence-Pack:** `docs/evidence/AF-02-01.md`
  >   **App-Testable:** `false`
  >   **Required-Failure-Modes:** `invalid profile rejected`
  >   **Preconditions:** `AF-01-02`
  >   **Target File:** `src/aetherflow/core/profiles.py`
  >   **Target File:** `src/aetherflow/core/diagnostics.py`
  >   **Target File:** `src/aetherflow/input/xinput.py`
  >   **Target File:** `src/aetherflow/input/playstation.py`
  >   **Target File:** `src/aetherflow/input/kbm.py`
  >   **Target File:** `tests/unit/test_profiles.py`
  >   **Target File:** `tests/integration/test_mapping_pipeline.py`
  >   **Target File:** `tests/integration/test_input_plugins.py`
  >   **Behavior:** implement profile CRUD, deterministic mapping, latency telemetry, and baseline device-family support.
  >   **Validation:** `uv run pytest tests/unit/test_profiles.py tests/integration/test_mapping_pipeline.py tests/integration/test_input_plugins.py`
  >   **Evidence:** profile and mapping behaviors are deterministic across device families.
  >   **Completion Gates:**
  > - Input plugins ingest real device events or test fixtures.
  > - Mapping pipeline includes latency telemetry outputs.
  > - CRUD and import/export flows are covered by tests.
  >   **ARP Trigger:** if latency or translation cannot be measured consistently, capture sample traces and stop.
- [x] `AF-02-02` Add virtual output, masking, and plugin-failure-safe output UX.
  > **PRD Refs:** `§9.3`, `§10.1`, `REQ-05`
  > **Role:** `native-io-capture`
  > **Feature-Class:** `ui`
  > **Entry-Point:** `driver status panel`
  > **Acceptance Criteria:**
  >
  > - AC1: Masking is reversible and survives failure.
  > - AC2: Driver panel reflects output-plugin state.
  >   **Required-Proof-Types:** `integration`
  >   **Evidence-Pack:** `docs/evidence/AF-02-02.md`
  >   **App-Testable:** `true`
  >   **App-Surface:** `driver-status-panel`
  >   **Required-Failure-Modes:** `driver masking failure surfaced`
  >   **Developer-Alert-Message:** `Output driver failure detected — check virtual controller and masking state`
  >   **Preconditions:** `AF-02-01`
  >   **Target File:** `src/aetherflow/output/virtual_controller.py`
  >   **Target File:** `src/aetherflow/output/device_masking.py`
  >   **Target File:** `src/aetherflow/ui/panels/driver_status_panel.py`
  >   **Target File:** `tests/integration/test_output_virtualization.py`
  >   **Target File:** `tests/ui/test_driver_panel.py`
  >   **Behavior:** implement reversible masking and output-driver UX while ensuring output-plugin failure degrades only that feature surface.
  >   **Validation:** `uv run pytest tests/integration/test_output_virtualization.py tests/ui/test_driver_panel.py`
  >   **Evidence:** host survives output-plugin faults and retains diagnostics.
  >   **Completion Gates:**
  > - Driver install/repair/masking flows are functional.
  > - Failure of output plugin degrades only the output surface.
  > - Tests verify reversibility and host survivability.
  >   **ARP Trigger:** if output failure can destabilize the shell, stop and capture the fault.

### Phase 2 Exit Criteria

```text
uv run ruff check .
uv run pytest tests/unit/test_profiles.py tests/integration/test_mapping_pipeline.py tests/integration/test_input_plugins.py tests/integration/test_output_virtualization.py tests/ui/test_driver_panel.py
```

---

## Phase 3 - Capture And Display Compliance

- [x] `AF-03-01` Implement OpenCV capture, mode matrix enforcement, and 60 FPS baseline validation.
  > **PRD Refs:** `§6.4`, `§9.4`, `REQ-06`
  > **Role:** `native-io-capture`
  > **Feature-Class:** `service`
  > **Entry-Point:** `opencv capture`
  > **Acceptance Criteria:**
  >
  > - AC1: Only supported capture modes are selectable.
  > - AC2: 60 FPS compliance is measurable.
  >   **Required-Proof-Types:** `integration`
  >   **Evidence-Pack:** `docs/evidence/AF-03-01.md`
  >   **App-Testable:** `false`
  >   **Required-Failure-Modes:** `unsupported capture mode rejected`
  >   **Performance-Claim:** `true`
  >   **Performance-Threshold:** `60 FPS sustained`
  >   **Performance-Evidence-Type:** `sustained-drop-detection`
  >   **Performance-Evidence-Location:** `tests/integration/test_capture_stability.py`
  >   **Preconditions:** `AF-02-01`, `AF-01-02`
  >   **Target File:** `src/aetherflow/vision/opencv_capture.py`
  >   **Target File:** `src/aetherflow/ui/panels/capture_panel.py`
  >   **Target File:** `src/aetherflow/core/capture_metrics.py`
  >   **Target File:** `tests/integration/test_capture_opencv.py`
  >   **Target File:** `tests/ui/test_capture_mode_matrix.py`
  >   **Target File:** `tests/integration/test_capture_stability.py`
  >   **Behavior:** implement supported-mode-only selection, sustained-drop detection, and 60 FPS compliance on supported hardware paths.
  >   **Validation:** `uv run pytest tests/integration/test_capture_opencv.py tests/ui/test_capture_mode_matrix.py tests/integration/test_capture_stability.py`
  >   **Evidence:** unsupported high-FPS modes are not implied by UI and 60 baseline behavior is measurable.
  >   **Completion Gates:**
  > - Device probing and capture start/stop are implemented.
  > - FPS and drop-rate measurements are real, not static tables.
  > - Tests cover sustained drops and capability matrix enforcement.
  >   **ARP Trigger:** if capability/UI mismatch occurs, capture hardware and mode diagnostics.
- [x] `AF-03-02` Add premium capture backends, CPU/GPU render modes, and one validated 120 FPS path.
  > **PRD Refs:** `§9.4`, `§9.5`, `§11`, `REQ-06`, `REQ-07`
  > **Role:** `native-io-capture`
  > **Feature-Class:** `service`
  > **Entry-Point:** `premium capture backends`
  > **Acceptance Criteria:**
  >
  > - AC1: Premium backends are locked when entitlement is locked.
  > - AC2: At least one validated 120 FPS path exists.
  >   **Required-Proof-Types:** `integration, e2e`
  >   **Evidence-Pack:** `docs/evidence/AF-03-02.md`
  >   **App-Testable:** `false`
  >   **Required-Failure-Modes:** `premium backend blocked when locked`
  >   **Performance-Claim:** `true`
  >   **Performance-Threshold:** `120 FPS validated path`
  >   **Performance-Evidence-Type:** `capability-enumeration`
  >   **Performance-Evidence-Location:** `tests/integration/test_capture_120fps_path.py`
  >   **Preconditions:** `AF-03-01`
  >   **Target File:** `src/aetherflow/vision/mf_capture.py`
  >   **Target File:** `src/aetherflow/vision/ds_capture.py`
  >   **Target File:** `src/aetherflow/ui/panels/render_mode_panel.py`
  >   **Target File:** `src/aetherflow/ui/panels/capture_diagnostics_panel.py`
  >   **Target File:** `tests/integration/test_capture_premium_gating.py`
  >   **Target File:** `tests/ui/test_render_modes.py`
  >   **Target File:** `tests/ui/test_capture_fallback_actions.py`
  >   **Target File:** `tests/integration/test_capture_120fps_path.py`
  >   **Target File:** `tests/e2e/test_capture_premium_e2e.py`
  >   **Behavior:** keep premium backends unloadable when locked, expose render tradeoffs clearly, and ship at least one validated 120 FPS path without promoting 240 FPS as guaranteed.
  >   **Validation:** `uv run pytest tests/integration/test_capture_premium_gating.py tests/ui/test_render_modes.py tests/ui/test_capture_fallback_actions.py tests/integration/test_capture_120fps_path.py tests/e2e/test_capture_premium_e2e.py`
  >   **Evidence:** one 120 FPS evidence path exists and premium gating holds.
  >   **Completion Gates:**
  > - Premium backends implement real capture behavior.
  > - Render mode UI is wired to runtime selection.
  > - 120 FPS evidence includes real measurement artifacts.
  >   **ARP Trigger:** if 120 validation is absent, phase stays incomplete even if 60 baseline passes.

### Phase 3 Exit Criteria

```text
uv run ruff check .
uv run pytest tests/integration/test_capture_opencv.py tests/ui/test_capture_mode_matrix.py tests/integration/test_capture_stability.py tests/integration/test_capture_premium_gating.py tests/ui/test_render_modes.py tests/ui/test_capture_fallback_actions.py tests/integration/test_capture_120fps_path.py tests/e2e/test_capture_premium_e2e.py
```

---

## Phase 4 - Worker Supervision And Environment Management

- [ ] `AF-04-01` Implement worker supervision with restart ceilings and escalation UX.
  > **PRD Refs:** `§6.2`, `§7`, `§9.7`, `§10.2`, `REQ-08`
  > **Role:** `runtime-services`
  > **Feature-Class:** `service`
  > **Entry-Point:** `host worker supervisor`
  > **Acceptance Criteria:**
  >
  > - AC1: Restart ceilings are enforced and logged.
  > - AC2: Escalation to FAILED occurs on ceiling breach.
  >   **Required-Proof-Types:** `unit, integration, stress, ui`
  >   **Evidence-Pack:** `docs/evidence/AF-04-01.md`
  >   **App-Testable:** `false`
  >   **Required-Failure-Modes:** `restart ceiling breach escalates to FAILED`
  >   **Preconditions:** `AF-00-03`, `AF-03-01`
  >   **Target File:** `host/` native supervision and IPC implementation files to be created for this phase
  >   **Target File:** `include/` native supervision and IPC headers to be created for this phase
  >   **Target File:** `src/aetherflow/ui/panels/worker_health_panel.py`
  >   **Target File:** `tests/integration/test_worker_supervisor.py`
  >   **Target File:** `tests/stress/test_worker_crash_loop.py`
  >   **Target File:** `tests/ui/test_worker_health_panel.py`
  >   **Behavior:** the current native surface is insufficient for PRD `§5.1`; this phase must create the missing host-side worker supervisor and IPC endpoint implementation boundary in native code. Supervision authority is host-owned; Python must not own start/stop/restart/heartbeat/escalation decisions and may only consume or relay authoritative host state.
  >   **Validation:** `uv run pytest tests/integration/test_worker_supervisor.py tests/stress/test_worker_crash_loop.py tests/ui/test_worker_health_panel.py`
  >   **Evidence:** host survivability is a hard phase gate.
  >   **Completion Gates:**
  > - Native host supervision and IPC implementation artifacts exist beyond the Phase 0 harness or ABI scaffold.
  > - Worker supervision is integrated with real worker processes.
  > - Host owns start, stop, restart, heartbeat, and escalation authority.
  > - Escalation UX is wired and tested under fault injection.
  > - Any Python worker supervisor code is reduced to a client adapter or retired; no Python-side supervisor-of-record logic remains.
  > - Restart ceilings persist and emit evidence logs.
  >   **ARP Trigger:** if host death or uncontrolled restart loops occur, block the phase.
- [ ] `AF-04-02` Deliver environment manager and bounded bundle validation workflow.
  > **PRD Refs:** `§9.8`, `REQ-09`
  > **Role:** `runtime-services`
  > **Feature-Class:** `service`
  > **Entry-Point:** `environment panel`
  > **Acceptance Criteria:**
  >
  > - AC1: Env create/repair/recreate operates on real environments.
  > - AC2: Bundle naming ambiguity does not block function.
  >   **Required-Proof-Types:** `integration`
  >   **Evidence-Pack:** `docs/evidence/AF-04-02.md`
  >   **App-Testable:** `true`
  >   **App-Surface:** `environment-panel`
  >   **Required-Failure-Modes:** `invalid bundle rejected`
  >   **Developer-Alert-Message:** `Environment validation failed — check bundle integrity and env configuration`
  >   **Preconditions:** `AF-00-05`, `AF-04-01`
  >   **Target File:** `src/aetherflow/core/env_manager.py`
  >   **Target File:** `src/aetherflow/core/bundle_installer.py`
  >   **Target File:** `src/aetherflow/ui/panels/environment_panel.py`
  >   **Target File:** `tests/unit/test_env_manager.py`
  >   **Target File:** `tests/test_bundle_installer.py`
  >   **Target File:** `tests/ui/test_environment_panel.py`
  >   **Behavior:** implement env create/repair/recreate/delete, required-import validation, optional GPU probe result shape, and bundle install fallback semantics from the sign-off packet.
  >   **Validation:** `uv run pytest tests/unit/test_env_manager.py tests/test_bundle_installer.py tests/ui/test_environment_panel.py`
  >   **Evidence:** environment validation is consistent and bundle naming ambiguity does not block function.
  >   **Completion Gates:**
  > - Env create/repair/recreate operates on real environments.
  > - Bundle signature verification is not hard-coded.
  > - GPU probe executes and emits required status values.
  >   **ARP Trigger:** if bundle validation depends on unresolved naming, use the documented fallback and keep moving.

### Phase 4 Exit Criteria

```text
uv run ruff check .
uv run pytest tests/integration/test_worker_supervisor.py tests/stress/test_worker_crash_loop.py tests/unit/test_env_manager.py tests/test_bundle_installer.py tests/ui/test_environment_panel.py
```

---

## Phase 5 - Online Resources, Admin, Packaging, And Evidence

- [ ] `AF-05-01` Build Online Resources trust flow with mock-provider fallback.
  > **PRD Refs:** `§8.1`, `§9.9`, `REQ-03`, `REQ-09`
  > **Role:** `trust-security`
  > **Feature-Class:** `service`
  > **Entry-Point:** `resources manifest`
  > **Acceptance Criteria:**
  >
  > - AC1: Signed manifests are validated before install.
  > - AC2: Mock fallback works when no auth provider is selected.
  >   **Required-Proof-Types:** `integration`
  >   **Evidence-Pack:** `docs/evidence/AF-05-01.md`
  >   **App-Testable:** `false`
  >   **Required-Failure-Modes:** `unsigned manifest rejected`
  >   **Preconditions:** `AF-00-05`, `AF-01-02`, `AF-04-02`
  >   **Target File:** `src/aetherflow/core/resources_manifest.py`
  >   **Target File:** `src/aetherflow/core/resources_client.py`
  >   **Target File:** `src/aetherflow/ui/panels/resources_panel.py`
  >   **Target File:** `src/aetherflow/ui/panels/resource_details_modal.py`
  >   **Target File:** `tests/integration/test_resources_manifest.py`
  >   **Target File:** `tests/ui/test_resource_details_modal.py`
  >   **Target File:** `tests/test_security.py`
  >   **Behavior:** validate signed manifests and artifact trust while using the provider-agnostic OAuth abstraction or disabled mock fallback if no auth provider is selected.
  >   **Validation:** `uv run pytest tests/integration/test_resources_manifest.py tests/ui/test_resource_details_modal.py tests/test_security.py`
  >   **Evidence:** no real provider binding is required to complete v1 resource UI/tests safely.
  >   **Completion Gates:**
  > - Manifest verification validates real signatures and trust roots.
  > - Resource install flows are implemented and tested.
  > - OAuth provider abstraction is functional (or explicit fallback).
  >   **ARP Trigger:** if resource trust depends on unresolved provider choice, use the fallback and document it.
- [ ] `AF-05-02` Implement admin, diagnostics export, packaging, and evidence collectors.
  > **PRD Refs:** `§9.10`, `§9.11`, `§12`, `§13`, `REQ-10`
  > **Role:** `runtime-services`
  > **Feature-Class:** `workflow`
  > **Entry-Point:** `admin diagnostics export`
  > **Acceptance Criteria:**
  >
  > - AC1: Admin actions update real data models.
  > - AC2: Diagnostics export includes real logs.
  >   **Required-Proof-Types:** `integration, e2e`
  >   **Evidence-Pack:** `docs/evidence/AF-05-02.md`
  >   **App-Testable:** `false`
  >   **Required-Failure-Modes:** `missing evidence artifact blocks release`
  >   **Preconditions:** `AF-05-01`
  >   **Target File:** `src/aetherflow/ui/panels/admin_panel.py`
  >   **Target File:** `src/aetherflow/core/audit_log.py`
  >   **Target File:** `src/aetherflow/core/diagnostics_export.py`
  >   **Target File:** `scripts/package-windows.ps1`
  >   **Target File:** `scripts/run-e2e.ps1`
  >   **Target File:** `tests/integration/test_admin_dashboard.py`
  >   **Target File:** `tests/integration/test_diagnostics_export.py`
  >   **Target File:** `tests/e2e/test_onboarding_timing.py`
  >   **Behavior:** ship admin/operator workflows, diagnostics export, Windows packaging, and evidence files for latency, survivability, bundle success, 60 FPS stability, and validated 120 FPS path.
  >   **Validation:** `uv run pytest tests/integration/test_admin_dashboard.py tests/integration/test_diagnostics_export.py tests/e2e/test_onboarding_timing.py`
  >   **Evidence:** required release artifacts exist under `logs/`.
  >   **Completion Gates:**
  > - Admin workflows update real data models and audit logs.
  > - Diagnostics export includes real logs and counters.
  > - Evidence artifacts are generated by tests, not stubs.
  >   **ARP Trigger:** missing evidence or rollback gaps block release readiness.

### Phase 5 Exit Criteria

```text
uv run ruff check .
uv run pytest
powershell -ExecutionPolicy Bypass -File scripts/package-windows.ps1
```

---

## Risk Register

| ID        | Area                  | Description                                                  | Mitigation                                                 | Related Items                      |
| --------- | --------------------- | ------------------------------------------------------------ | ---------------------------------------------------------- | ---------------------------------- |
| `RISK-01` | Canonical paths       | Repo/document drift causes implementation in the wrong tree  | Canonicalize early and enforce via tests                   | `AF-00-01`                         |
| `RISK-02` | Tooling               | Windows/WSL mismatch breaks reproducibility                  | Verify boundary and shell behavior before freeze           | `AF-00-02a`, `AF-00-02b`           |
| `RISK-03` | Weak trust policy     | Under-specified signing could allow weak verification        | Freeze Authenticode + RSA-3072 semantics in ABI/docs/tests | `AF-00-04`, `AF-01-01`             |
| `RISK-04` | Performance ambiguity | Latency and capture compliance drift without numeric budgets | Encode budgets in PRD and phase validations                | `AF-00-03`, `AF-03-01`, `AF-03-02` |
| `RISK-05` | Failure UX regression | Plugin or worker faults destabilize the host shell           | Publish and test host-safe degradation model               | `AF-00-05`, `AF-01-02`, `AF-04-01` |

---

## Traceability Matrix

line-grow note: this traceability matrix stays wide so section mappings remain
scannable as a single table.

<!-- markdownlint-disable MD060 -->

| PRD Section                    | Requirement IDs              | Work Item IDs                                                | Status   |
| ------------------------------ | ---------------------------- | ------------------------------------------------------------ | -------- |
| `§5`                           | `REQ-01`                     | `AF-00-01`, `AF-00-02a`, `AF-00-02b`, `AF-00-03`, `AF-00-04` | Planned  |
| `§6`                           | `REQ-02`, `REQ-06`, `REQ-08` | `AF-00-03`, `AF-03-01`, `AF-04-01`                           | Planned  |
| `§7`, `§7.4`                   | `REQ-02`, `REQ-08`           | `AF-00-03`, `AF-01-02`, `AF-04-01`                           | Planned  |
| `§8`                           | `REQ-02`, `REQ-03`           | `AF-00-04`, `AF-01-01`, `AF-01-02`                           | Planned  |
| `§9.1`, `§9.9`                 | `REQ-03`                     | `AF-01-01`, `AF-05-01`                                       | Planned  |
| `§9.2`, `§9.6`                 | `REQ-04`                     | `AF-02-01`                                                   | Planned  |
| `§9.3`                         | `REQ-05`                     | `AF-02-02`                                                   | Planned  |
| `§9.4`                         | `REQ-06`                     | `AF-03-01`, `AF-03-02`                                       | Planned  |
| `§9.5`, `§11`                  | `REQ-07`                     | `AF-01-02`, `AF-03-02`                                       | Planned  |
| `§9.7`, `§10.2`                | `REQ-08`                     | `AF-04-01`                                                   | Planned  |
| `§9.8`                         | `REQ-09`                     | `AF-00-05`, `AF-04-02`                                       | Planned  |
| `§9.10`, `§9.11`, `§12`, `§13` | `REQ-10`                     | `AF-05-02`                                                   | Planned  |
| `§14`                          | `ASM-02`, `ASM-03`           | `AF-00-05`, `AF-04-02`, `AF-05-01`                           | Planned  |
| `§15`, `§9.12`                 | `ASM-04`                     | `None (deferred out of v1)`                                  | Deferred |
| `§15`, `§9.13`, `§9.14`        | `Deferred scope only`        | `None (deferred out of v1)`                                  | Deferred |

<!-- markdownlint-enable MD060 -->

---

## Follow-up Tasks For Scaffolded Areas

These follow-ups are required before any phase can advance to "verified"
status. They are evidence-driven and should become work items as needed.

- **Trust/Security hardening**
  - Replace hard-coded signature checks with real verification paths.
  - Add tests for unsigned, revoked, expired, and tampered artifacts.
- **Input/Output runtime wiring**
  - Implement device ingestion and event pipeline for input plugins.
  - Implement output driver install/repair and masking flows.
- **Capture/runtime realism**
  - Implement device probing and capture start/stop integration.
  - Emit real FPS and drop-rate metrics with evidence artifacts.
- **Delivery-unit alignment**
  - Use `docs/architecture/delivery-architecture-alignment-notes.md`
    section 5.0 as the source of truth for shipped, implement-before-ship,
    and excluded feature delivery units.
  - Treat shipped feature rows without a host loader path or helper launch
    path as release blockers.
- **Environment/Resources workflows**
  - Implement real env create/repair/recreate and GPU probe paths.
  - Implement resource download/install with trust checks.
- **Admin/Diagnostics evidence**
  - Wire admin actions to audit logs and persistence.
  - Expand diagnostics export to include real logs and counters.

---

## Next Recommended Implementation Order

1. Complete `AF-00-01` through `AF-00-05` without skipping the contract-freeze sequence.
2. Move to `AF-01-01` and `AF-01-02` so trust, entitlement, and host-safe degradation exist before feature delivery.
3. Complete Phases 2 and 3 before worker, resource, and packaging phases so runtime evidence has real feature surfaces to validate.
