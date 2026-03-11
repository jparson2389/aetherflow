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
- Scope is Windows v1 `P0` only. Deferred: `PRD-§9.6`, `PRD-§14` protected-model
  cryptosystem work, remote-play, and high-frequency scripting.
- Frozen contracts after Phase 0: `include/plugin_system.hpp`,
  `proto/capture.proto`, `src/aetherflow/core/shared_memory_layout.py`.
- Entitlement state machine freezes after Phase 4:
  `src/aetherflow/core/entitlements.py`.
- Mandatory validation for completed work remains `uv run ruff check .` and
  `uv run pytest`.
- TDD is required on every work item.

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
  lands under `src/aetherflow/core/ipc/`.
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
- `docs/PRD.md`: runtime budgets, failure UX, and validated capture guarantees.

---

## Requirement Ledger

| ID       | PRD Ref               | Type                   | Summary                                                       | Dependencies                 | Verification                        |
| -------- | --------------------- | ---------------------- | ------------------------------------------------------------- | ---------------------------- | ----------------------------------- |
| `REQ-01` | `§5`                  | Constraint             | Windows-only microkernel host and frozen contracts            | none                         | contract and docs tests             |
| `REQ-02` | `§6`, `§7`, `§8`      | Security               | Numeric budgets, trust baseline, premium gating               | `REQ-01`                     | contract and policy tests           |
| `REQ-03` | `§9.1`, `§9.9`        | Functional             | Signed plugin and resource loading with explicit trust checks | `REQ-02`                     | loader and security tests           |
| `REQ-04` | `§9.2`, `§9.6`        | Functional             | Profiles, mapping, translation, input devices                 | `REQ-01`                     | profile and mapping tests           |
| `REQ-05` | `§9.3`, `§10.1`       | Functional/UX          | Virtual output, masking, host-safe plugin failure handling    | `REQ-04`                     | output and host survivability tests |
| `REQ-06` | `§9.4`, `§10.3`       | Functional/Performance | Capture 60 baseline, 120 validated path, capability-bound 240 | `REQ-02`, `REQ-03`           | capture compliance tests            |
| `REQ-07` | `§9.5`, `§11`         | UX                     | CPU/GPU render modes and always-visible status HUD            | `REQ-03`, `REQ-06`           | UI tests                            |
| `REQ-08` | `§9.7`, `§10.2`       | Functional/Ops         | Worker supervision, escalation ceilings, failure UX           | `REQ-02`                     | worker stress tests                 |
| `REQ-09` | `§9.8`, `§9.9`        | Functional             | Environment management and bundle validation                  | `REQ-08`                     | env and bundle tests                |
| `REQ-10` | `§9.10`, `§12`, `§13` | Operations             | Admin, diagnostics, packaging, evidence artifacts             | `REQ-03`, `REQ-08`, `REQ-09` | integration and e2e tests           |

---

## Phase 0 - Canonical Identity And Execution Contracts

- [ ] `AF-00-01` Canonicalize repo identity and self-contained docs.
  > **PRD Refs:** `§1`, `§2`, `REQ-01`
  > **Preconditions:** none
  > **Target File:** `docs/PRD.md`
  > **Target File:** `README.md`
  > **Target File:** `.agents/rules/project-specific.md`
  > **Target File:** `tests/contracts/test_canonical_identity.py`
  > **Target File:** `tests/contracts/test_prd_execution_readiness.py`
  > **Behavior:** remove stale aliases, keep PRD self-contained, and enforce canonical Python/C++ boundaries.
  > **Validation:** `uv run pytest tests/contracts/test_canonical_identity.py::test_canonical_package_root_is_aetherflow tests/contracts/test_canonical_identity.py::test_project_docs_reference_aetherflow_canonical_paths tests/contracts/test_prd_execution_readiness.py::test_prd_is_self_contained_and_citation_free`
  > **Evidence:** docs are citation-free and path-correct.
  > **ARP Trigger:** if any canonical path conflicts with active repo structure, stop and capture the conflict.
- [ ] `AF-00-02a` Verify Windows toolchain and `uv` environment.
  > **PRD Refs:** `§5.3`, `REQ-01`
  > **Preconditions:** `AF-00-01`
  > **Target File:** `scripts/verify-env.ps1`
  > **Target File:** `tests/contracts/test_env_readiness.py`
  > **Behavior:** verify `uv`, `powershell`, and `cl.exe` (MSVC) are available and functional.
  > **Validation:** `uv run pytest tests/contracts/test_env_readiness.py`
  > **Evidence:** environment report generated.
  > **ARP Trigger:** if toolchain is missing, halt execution until resolved.
- [ ] `AF-00-02b` Establish native boundary and build harness.
  > **PRD Refs:** `§5.3`, `REQ-01`
  > **Preconditions:** `AF-00-02a`
  > **Target File:** `host/`
  > **Target File:** `include/`
  > **Target File:** `scripts/build-native.ps1`
  > **Target File:** `tests/contracts/test_native_harness.py`
  > **Behavior:** scaffold `host/` and `include/` structure, create build script, and verify compilation of a minimal dummy target.
  > **Validation:** `powershell -ExecutionPolicy Bypass -File scripts/build-native.ps1`
  > **Evidence:** build artifacts present in `build/`.
  > **ARP Trigger:** if build fails, capture compiler output and stop.
- [ ] `AF-00-03` Publish control-plane proto surface and shared-memory ring semantics.
  > **PRD Refs:** `§6`, `§7`, `REQ-01`, `REQ-02`, `REQ-08`
  > **Preconditions:** `AF-00-02b`
  > **Target File:** `proto/capture.proto`
  > **Target File:** `src/aetherflow/core/shared_memory_layout.py`
  > **Target File:** `docs/proto/capture.md`
  > **Target File:** `tests/contracts/test_execution_contracts.py`
  > **Behavior:** publish the normative gRPC message surface, timeout/retry expectations, ring metadata, pixel labels, and overflow policy.
  > **Validation:** `uv run pytest tests/contracts/test_execution_contracts.py -k proto or overflow`
  > **Evidence:** proto and shmem contracts match PRD execution semantics.
  > **ARP Trigger:** if control-plane or ring semantics remain ambiguous, do not freeze them.
- [ ] `AF-00-04` Publish signing and runtime-state ABI, then freeze contracts.
  > **PRD Refs:** `§5.3`, `§7`, `§8`, `REQ-02`, `REQ-03`
  > **Preconditions:** `AF-00-03`
  > **Target File:** `include/plugin_system.hpp`
  > **Target File:** `docs/breaking-changes/abi.md`
  > **Target File:** `docs/breaking-changes/proto.md`
  > **Target File:** `docs/breaking-changes/shmem.md`
  > **Target File:** `tests/contracts/test_execution_contracts.py`
  > **Target File:** `tests/contracts/test_frozen_contracts.py`
  > **Behavior:** publish Authenticode/RSA-3072 trust semantics, plugin runtime states, and freeze ABI/proto/shmem in one checkpoint.
  > **Validation:** `uv run pytest tests/contracts/test_execution_contracts.py tests/contracts/test_frozen_contracts.py`
  > **Evidence:** trust and state semantics are documented and frozen together.
  > **ARP Trigger:** if trust policy or runtime states are still in flux, stop instead of publishing the freeze.
- [ ] `AF-00-05` Publish bounded sign-off packets and failure-UX state model.
  > **PRD Refs:** `§8.3`, `§10`, `§14`, `REQ-02`, `REQ-08`, `REQ-09`
  > **Preconditions:** `AF-00-04`
  > **Target File:** `docs/sign-offs/auth-provider.md`
  > **Target File:** `docs/sign-offs/bundle-format.md`
  > **Target File:** `tests/contracts/test_prd_execution_readiness.py`
  > **Behavior:** encode auth/bundle deadlines, fallbacks, and the host/plugin/worker degraded-state model so agents do not stall.
  > **Validation:** `uv run pytest tests/contracts/test_prd_execution_readiness.py -k plan`
  > **Evidence:** unresolved product decisions have explicit fallbacks and phase gates.
  > **ARP Trigger:** if a sign-off packet lacks fallback behavior, downstream work remains blocked.

### Phase 0 Exit Criteria

```text
uv run ruff check .
uv run pytest tests/contracts
powershell -ExecutionPolicy Bypass -File scripts/build-native.ps1
```

---

## Phase 1 - Trust, Entitlements, And Shell Resilience

- [ ] `AF-01-01` Implement trust verification and plugin/resource catalog policy.
  > **PRD Refs:** `§8.1`, `§9.1`, `§9.9`, `REQ-02`, `REQ-03`
  > **Preconditions:** `AF-00-04`
  > **Target File:** `src/aetherflow/plugins/trust.py`
  > **Target File:** `src/aetherflow/plugins/registry.py`
  > **Target File:** `src/aetherflow/plugins/catalog.py`
  > **Target File:** `tests/unit/test_plugin_registry.py`
  > **Target File:** `tests/integration/test_signed_plugin_loading.py`
  > **Target File:** `tests/test_security.py`
  > **Behavior:** enforce Authenticode-rooted trust semantics and block unsigned/tampered/untrusted content before load or install.
  > **Validation:** `uv run pytest tests/unit/test_plugin_registry.py tests/integration/test_signed_plugin_loading.py tests/test_security.py`
  > **Evidence:** load/install refusal occurs before registration or activation.
  > **ARP Trigger:** any reachable unsigned path blocks the phase.
- [ ] `AF-01-02` Implement entitlement runtime states and shell-safe degradation model.
  > **PRD Refs:** `§8.2`, `§8.3`, `§10.1`, `REQ-02`, `REQ-07`
  > **Preconditions:** `AF-01-01`
  > **Target File:** `src/aetherflow/core/entitlements.py`
  > **Target File:** `src/aetherflow/ui/shell.py`
  > **Target File:** `src/aetherflow/ui/router.py`
  > **Target File:** `src/aetherflow/ui/status_hud.py`
  > **Target File:** `tests/unit/test_entitlements.py`
  > **Target File:** `tests/integration/test_plugin_catalog_locking.py`
  > **Target File:** `tests/ui/test_status_hud.py`
  > **Behavior:** implement `LOCKED`, `GRACE`, `DEGRADED`, `FAILED`, and HUD semantics without allowing plugin faults to take down the shell.
  > **Validation:** `uv run pytest tests/unit/test_entitlements.py tests/integration/test_plugin_catalog_locking.py tests/ui/test_status_hud.py`
  > **Evidence:** shell remains alive when plugins degrade or unload.
  > **ARP Trigger:** if plugin failure can terminate the shell, stop and capture the crash path.

### Phase 1 Exit Criteria

```text
uv run ruff check .
uv run pytest tests/unit/test_plugin_registry.py tests/unit/test_entitlements.py tests/integration/test_signed_plugin_loading.py tests/integration/test_plugin_catalog_locking.py tests/ui/test_status_hud.py tests/test_security.py
```

---

## Phase 2 - Controller Core, Input Layer, And Output Virtualization

- [ ] `AF-02-01` Deliver profiles, mapping, translation, diagnostics, and input plugins.
  > **PRD Refs:** `§6.1`, `§9.2`, `§9.6`, `REQ-04`
  > **Preconditions:** `AF-01-02`
  > **Target File:** `src/aetherflow/core/profiles.py`
  > **Target File:** `src/aetherflow/core/diagnostics.py`
  > **Target File:** `src/aetherflow/input/xinput.py`
  > **Target File:** `src/aetherflow/input/playstation.py`
  > **Target File:** `src/aetherflow/input/kbm.py`
  > **Target File:** `tests/unit/test_profiles.py`
  > **Target File:** `tests/integration/test_mapping_pipeline.py`
  > **Target File:** `tests/integration/test_input_plugins.py`
  > **Behavior:** implement profile CRUD, deterministic mapping, latency telemetry, and baseline device-family support.
  > **Validation:** `uv run pytest tests/unit/test_profiles.py tests/integration/test_mapping_pipeline.py tests/integration/test_input_plugins.py`
  > **Evidence:** profile and mapping behaviors are deterministic across device families.
  > **ARP Trigger:** if latency or translation cannot be measured consistently, capture sample traces and stop.
- [ ] `AF-02-02` Add virtual output, masking, and plugin-failure-safe output UX.
  > **PRD Refs:** `§9.3`, `§10.1`, `REQ-05`
  > **Preconditions:** `AF-02-01`
  > **Target File:** `src/aetherflow/output/virtual_controller.py`
  > **Target File:** `src/aetherflow/output/device_masking.py`
  > **Target File:** `src/aetherflow/ui/panels/driver_status_panel.py`
  > **Target File:** `tests/integration/test_output_virtualization.py`
  > **Target File:** `tests/ui/test_driver_panel.py`
  > **Behavior:** implement reversible masking and output-driver UX while ensuring output-plugin failure degrades only that feature surface.
  > **Validation:** `uv run pytest tests/integration/test_output_virtualization.py tests/ui/test_driver_panel.py`
  > **Evidence:** host survives output-plugin faults and retains diagnostics.
  > **ARP Trigger:** if output failure can destabilize the shell, stop and capture the fault.

### Phase 2 Exit Criteria

```text
uv run ruff check .
uv run pytest tests/unit/test_profiles.py tests/integration/test_mapping_pipeline.py tests/integration/test_input_plugins.py tests/integration/test_output_virtualization.py tests/ui/test_driver_panel.py
```

---

## Phase 3 - Capture And Display Compliance

- [ ] `AF-03-01` Implement OpenCV capture, mode matrix enforcement, and 60 FPS baseline validation.
  > **PRD Refs:** `§6.4`, `§9.4`, `REQ-06`
  > **Preconditions:** `AF-02-01`, `AF-01-02`
  > **Target File:** `src/aetherflow/vision/opencv_capture.py`
  > **Target File:** `src/aetherflow/ui/panels/capture_panel.py`
  > **Target File:** `src/aetherflow/core/capture_metrics.py`
  > **Target File:** `tests/integration/test_capture_opencv.py`
  > **Target File:** `tests/ui/test_capture_mode_matrix.py`
  > **Target File:** `tests/integration/test_capture_stability.py`
  > **Behavior:** implement supported-mode-only selection, sustained-drop detection, and 60 FPS compliance on supported hardware paths.
  > **Validation:** `uv run pytest tests/integration/test_capture_opencv.py tests/ui/test_capture_mode_matrix.py tests/integration/test_capture_stability.py`
  > **Evidence:** unsupported high-FPS modes are not implied by UI and 60 baseline behavior is measurable.
  > **ARP Trigger:** if capability/UI mismatch occurs, capture hardware and mode diagnostics.
- [ ] `AF-03-02` Add premium capture backends, CPU/GPU render modes, and one validated 120 FPS path.
  > **PRD Refs:** `§9.4`, `§9.5`, `§11`, `REQ-06`, `REQ-07`
  > **Preconditions:** `AF-03-01`
  > **Target File:** `src/aetherflow/vision/mf_capture.py`
  > **Target File:** `src/aetherflow/vision/ds_capture.py`
  > **Target File:** `src/aetherflow/ui/panels/render_mode_panel.py`
  > **Target File:** `src/aetherflow/ui/panels/capture_diagnostics_panel.py`
  > **Target File:** `tests/integration/test_capture_premium_gating.py`
  > **Target File:** `tests/ui/test_render_modes.py`
  > **Target File:** `tests/ui/test_capture_fallback_actions.py`
  > **Target File:** `tests/integration/test_capture_120fps_path.py`
  > **Behavior:** keep premium backends unloadable when locked, expose render tradeoffs clearly, and ship at least one validated 120 FPS path without promoting 240 FPS as guaranteed.
  > **Validation:** `uv run pytest tests/integration/test_capture_premium_gating.py tests/ui/test_render_modes.py tests/ui/test_capture_fallback_actions.py tests/integration/test_capture_120fps_path.py`
  > **Evidence:** one 120 FPS evidence path exists and premium gating holds.
  > **ARP Trigger:** if 120 validation is absent, phase stays incomplete even if 60 baseline passes.

### Phase 3 Exit Criteria

```text
uv run ruff check .
uv run pytest tests/integration/test_capture_opencv.py tests/ui/test_capture_mode_matrix.py tests/integration/test_capture_stability.py tests/integration/test_capture_premium_gating.py tests/ui/test_render_modes.py tests/ui/test_capture_fallback_actions.py tests/integration/test_capture_120fps_path.py
```

---

## Phase 4 - Worker Supervision And Environment Management

- [ ] `AF-04-01` Implement worker supervision with restart ceilings and escalation UX.
  > **PRD Refs:** `§6.2`, `§7`, `§9.7`, `§10.2`, `REQ-08`
  > **Preconditions:** `AF-00-03`, `AF-03-01`
  > **Target File:** `src/aetherflow/core/worker_supervisor.py`
  > **Target File:** `src/aetherflow/ui/panels/worker_health_panel.py`
  > **Target File:** `tests/integration/test_worker_supervisor.py`
  > **Target File:** `tests/stress/test_worker_crash_loop.py`
  > **Behavior:** enforce heartbeat budgets, restart ceilings, escalation to `FAILED`, and host-safe worker degradation.
  > **Validation:** `uv run pytest tests/integration/test_worker_supervisor.py tests/stress/test_worker_crash_loop.py`
  > **Evidence:** host survivability is a hard phase gate.
  > **ARP Trigger:** if host death or uncontrolled restart loops occur, block the phase.
- [ ] `AF-04-02` Deliver environment manager and bounded bundle validation workflow.
  > **PRD Refs:** `§9.8`, `REQ-09`
  > **Preconditions:** `AF-00-05`, `AF-04-01`
  > **Target File:** `src/aetherflow/core/env_manager.py`
  > **Target File:** `src/aetherflow/core/bundle_installer.py`
  > **Target File:** `src/aetherflow/ui/panels/environment_panel.py`
  > **Target File:** `tests/unit/test_env_manager.py`
  > **Target File:** `tests/test_bundle_installer.py`
  > **Behavior:** implement env create/repair/recreate/delete, required-import validation, optional GPU probe result shape, and bundle install fallback semantics from the sign-off packet.
  > **Validation:** `uv run pytest tests/unit/test_env_manager.py tests/test_bundle_installer.py`
  > **Evidence:** environment validation is consistent and bundle naming ambiguity does not block function.
  > **ARP Trigger:** if bundle validation depends on unresolved naming, use the documented fallback and keep moving.

### Phase 4 Exit Criteria

```text
uv run ruff check .
uv run pytest tests/integration/test_worker_supervisor.py tests/stress/test_worker_crash_loop.py tests/unit/test_env_manager.py tests/test_bundle_installer.py
```

---

## Phase 5 - Online Resources, Admin, Packaging, And Evidence

- [ ] `AF-05-01` Build Online Resources trust flow with mock-provider fallback.
  > **PRD Refs:** `§8.1`, `§9.9`, `REQ-03`, `REQ-09`
  > **Preconditions:** `AF-00-05`, `AF-01-02`, `AF-04-02`
  > **Target File:** `src/aetherflow/core/resources_manifest.py`
  > **Target File:** `src/aetherflow/core/resources_client.py`
  > **Target File:** `src/aetherflow/ui/panels/resources_panel.py`
  > **Target File:** `src/aetherflow/ui/panels/resource_details_modal.py`
  > **Target File:** `tests/integration/test_resources_manifest.py`
  > **Target File:** `tests/ui/test_resource_details_modal.py`
  > **Target File:** `tests/test_security.py`
  > **Behavior:** validate signed manifests and artifact trust while using the provider-agnostic OAuth abstraction or disabled mock fallback if no auth provider is selected.
  > **Validation:** `uv run pytest tests/integration/test_resources_manifest.py tests/ui/test_resource_details_modal.py tests/test_security.py`
  > **Evidence:** no real provider binding is required to complete v1 resource UI/tests safely.
  > **ARP Trigger:** if resource trust depends on unresolved provider choice, use the fallback and document it.
- [ ] `AF-05-02` Implement admin, diagnostics export, packaging, and evidence collectors.
  > **PRD Refs:** `§12`, `§13`, `REQ-10`
  > **Preconditions:** `AF-05-01`
  > **Target File:** `src/aetherflow/ui/panels/admin_panel.py`
  > **Target File:** `src/aetherflow/core/audit_log.py`
  > **Target File:** `src/aetherflow/core/diagnostics_export.py`
  > **Target File:** `scripts/package-windows.ps1`
  > **Target File:** `scripts/run-e2e.ps1`
  > **Target File:** `tests/integration/test_admin_dashboard.py`
  > **Target File:** `tests/integration/test_diagnostics_export.py`
  > **Target File:** `tests/e2e/test_onboarding_timing.py`
  > **Behavior:** ship admin/operator workflows, diagnostics export, Windows packaging, and evidence files for latency, survivability, bundle success, 60 FPS stability, and validated 120 FPS path.
  > **Validation:** `uv run pytest tests/integration/test_admin_dashboard.py tests/integration/test_diagnostics_export.py tests/e2e/test_onboarding_timing.py`
  > **Evidence:** required release artifacts exist under `logs/`.
  > **ARP Trigger:** missing evidence or rollback gaps block release readiness.

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

| PRD Section           | Requirement IDs              | Work Item IDs                                                | Status  |
| --------------------- | ---------------------------- | ------------------------------------------------------------ | ------- |
| `§5`                  | `REQ-01`                     | `AF-00-01`, `AF-00-02a`, `AF-00-02b`, `AF-00-03`, `AF-00-04` | Planned |
| `§6`                  | `REQ-02`, `REQ-06`, `REQ-08` | `AF-00-03`, `AF-03-01`, `AF-04-01`                           | Planned |
| `§7`                  | `REQ-02`, `REQ-08`           | `AF-00-03`, `AF-01-02`, `AF-04-01`                           | Planned |
| `§8`                  | `REQ-02`, `REQ-03`           | `AF-00-04`, `AF-01-01`, `AF-01-02`                           | Planned |
| `§9.1`, `§9.9`        | `REQ-03`                     | `AF-01-01`, `AF-05-01`                                       | Planned |
| `§9.2`, `§9.6`        | `REQ-04`                     | `AF-02-01`                                                   | Planned |
| `§9.3`                | `REQ-05`                     | `AF-02-02`                                                   | Planned |
| `§9.4`                | `REQ-06`                     | `AF-03-01`, `AF-03-02`                                       | Planned |
| `§9.5`, `§11`         | `REQ-07`                     | `AF-01-02`, `AF-03-02`                                       | Planned |
| `§9.7`, `§10.2`       | `REQ-08`                     | `AF-04-01`                                                   | Planned |
| `§9.8`                | `REQ-09`                     | `AF-00-05`, `AF-04-02`                                       | Planned |
| `§9.10`, `§12`, `§13` | `REQ-10`                     | `AF-05-02`                                                   | Planned |
| `§14`                 | `ASM-02`, `ASM-03`, `ASM-04` | `AF-00-05`, `AF-04-02`, `AF-05-01`                           | Planned |

---

## Next Recommended Implementation Order

1. Complete `AF-00-01` through `AF-00-05` without skipping the contract-freeze sequence.
2. Move to `AF-01-01` and `AF-01-02` so trust, entitlement, and host-safe degradation exist before feature delivery.
3. Complete Phases 2 and 3 before worker, resource, and packaging phases so runtime evidence has real feature surfaces to validate.
