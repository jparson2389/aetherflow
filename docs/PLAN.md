# Aetherflow Windows v1 P0 Implementation Plan

## Summary

Grounded in `docs/PRD.md`, `AGENTS.md`, and `docs/architecture/system_overview.md`.

Source anchors verified in-repo on March 8, 2026:

- `AGENTS.md`
- `docs/architecture/system_overview.md`

Rules for this plan:

- Canonical product/package name is `Aetherflow`; Phase 0 must remove stale `Aetherlink` references from docs/rules before feature work.
- Scope is Windows v1 `P0` only. Deferred from this plan: `PRD-§5.7`, `PRD-§5.8.1`, `PRD-§5.8.2`, `PRD-§5.11.3`.
- Frozen contracts after Phase 0: `include/plugin_system.hpp`, `proto/capture.proto`, `src/aetherflow/core/shared_memory_layout.py`.
- Entitlement state machine freezes after Phase 4: `src/aetherflow/core/entitlements.py`.
- Forbidden changes: no `src/plugins/*`, no unsigned artifact execution, no premium DLL load without valid/GRACE entitlement, no worker-to-host bypass of gRPC + shared memory.
- Mandatory validations for every completed item: `uv run ruff check .` and `uv run pytest`.
- TDD is required on every work item.

## Assumptions And Sign-Off Gates

- `[ASM-01]` `src/aetherflow/` is the canonical package root; stale `aetherlink` references are documentation debt, not implementation truth.
- `[ASM-02]` `proto/` is the authoritative proto source in this repo; generated Python should land under `src/aetherflow/core/ipc/`.
- `[ASM-03]` Native C++20 code must stay under repo-root `host/` and `include/`; no C++ source or headers belong under `src/`.
- `[ASM-04]` Auth provider selection remains unresolved. Decision deadline: before `AF-05-01` starts. If no sign-off is supplied, implement only a provider-agnostic OAuth interface plus a disabled `MockOAuthProvider` to unblock resources UI/tests without shipping a real provider binding.
- `[ASM-05]` Aetherflow environment bundle term/extension/schema remains unresolved. Decision deadline: before `AF-04-02` starts. If no sign-off is supplied, implement a signed archive with internal `bundle.json` metadata and leave the external bundle extension unfrozen until human sign-off.
- `[ASM-06]` Phase 0 must verify a Windows-hosted `uv` workflow because the current shell wrapper could not execute `uv` directly.

## Public Interfaces / Contracts

- `plugin_system.hpp`: native plugin ABI for identity, lifecycle, capabilities, and entitlement/worker policy.
- `proto/capture.proto`: gRPC control-plane contract for capture control, worker health, logs, and results.
- `shared_memory_layout.py`: frame ring-buffer schema for the data plane.
- `entitlements.py`: entitlement token, GRACE/LOCKED/LOADED transitions, role model, TTL cache rules.
- Bundle schema and resource-auth contract are Phase 0 sign-off artifacts with explicit fallback behavior if sign-off misses the deadlines above.

## Requirement Ledger

| ID | PRD Ref | Type | Summary | Dependencies | Verification |
| --- | --- | --- | --- | --- | --- |
| `REQ-01` | `§1`, `§4.1-§4.5` | Constraint | Windows-only microkernel host; plugin-everything model; frozen contracts and guardrails enforced | none | contract tests + docs parity |
| `REQ-02` | `§2.1`, `§5.1`, `§7` | Functional/Security | Signed native plugin system with premium gating, GRACE handling, runtime load/unload, locked catalog UX | `REQ-01` | plugin loader + entitlement tests |
| `REQ-03` | `§3`, `§5.12` | Functional | Role-based access boundaries for gamer, tinkerer, modder, and admin/operator | `REQ-02` | RBAC tests |
| `REQ-04` | `§5.2` | Functional | Profiles, mapping, translation, fast switching, latency diagnostics | `REQ-01` | unit + integration mapping tests |
| `REQ-05` | `§5.3` | Functional/UX | Virtual output, masking, driver status, install/repair flows | `REQ-04` | integration + UI tests |
| `REQ-06` | `§5.4` | Functional/UX | OpenCV default capture, capability matrix, OBS fixed plugin, premium MF/DS plugins, stability metrics | `REQ-02` | capture integration tests |
| `REQ-07` | `§5.5`, `§6` | Functional/UX | CPU/GPU render modes and always-visible status HUD | `REQ-02`, `REQ-06` | UI tests |
| `REQ-08` | `§5.6` | Functional | XInput, PlayStation, legacy PS, and KBM ingestion plugins | `REQ-04` | device-plugin tests |
| `REQ-09` | `§5.9` | Functional/Ops | Out-of-process Python workers with gRPC control plane, shared memory, supervision, restart/backoff, UI logs/health | `REQ-01` | integration + stress tests |
| `REQ-10` | `§5.10` | Functional/UX | UI-managed uv environments and one-click signed bundle install with streamed logs | `REQ-09` | env manager + bundle tests |
| `REQ-11` | `§5.11.1`, `§5.11.2`, `§5.11.4` | Functional/Security | Signed resource manifest, artifact install, premium lock state, OAuth-ready auth support | `REQ-02`, `REQ-10` | resource/security tests |
| `REQ-12` | `§5.12`, `§7` | Functional/Security | Admin dashboard for users, roles, entitlements, revocations, audit log | `REQ-03` | admin tests |
| `REQ-13` | `§8`, `§9` | Operations | Windows packaging, updater/rollback, diagnostics export, success-metric evidence artifacts | `REQ-02`, `REQ-09`, `REQ-10`, `REQ-12` | packaging + evidence tests |
| `REQ-14` | `§2.2` | Non-goal | Exclude non-goals and deferred P1 features from MVP implementation | none | traceability review |

## Phase 0 - Canonical Foundation And Contract Freeze

- [ ] `AF-00-01` Canonicalize repo identity and path rules. `PRD Refs:` `§1`, `§4.4`, `§4.5`, `REQ-01`, `REQ-14`. `Preconditions:` none. `Target Files:` `docs/PRD.md`, `AGENTS.md`, `.agents/rules/project-specific.md`, `README.md`, `src/aetherflow/main.py`, top-level `main.py`. `Test Files:` `tests/contracts/test_canonical_identity.py`. `Behavior:` remove stale `Aetherlink`/path references, declare `src/aetherflow/` + `proto/` as canonical, and eliminate duplicate entrypoint ambiguity. `Validation:` `uv run pytest tests/contracts/test_canonical_identity.py`. `Evidence:` docs and tests agree on product/package/path names. `ARP Trigger:` if canonical paths conflict with active user files, stop and capture the conflicting path map.
- [ ] `AF-00-02` Verify Windows toolchain and native boundary. `PRD Refs:` `§4.4`, `§4.5`, `REQ-01`. `Preconditions:` `AF-00-01`. `Target Files:` `host/`, `include/`, `scripts/build-native.ps1`, `tests/contracts/test_frozen_contracts.py`. `Behavior:` verify the repo-root native boundary, add a repeatable Windows harness script, and prove the toolchain assumptions without freezing any contracts yet. `Validation:` `uv run pytest tests/contracts/test_frozen_contracts.py -k build_script`. `Evidence:` host/include boundaries exist and the build harness references the canonical contract inputs. `ARP Trigger:` if `uv` or the Windows shell cannot execute from the expected host, stop before freezing contracts and capture the failing environment details.
- [ ] `AF-00-03` Freeze ABI, proto, and shared-memory contracts. `PRD Refs:` `§4.4`, `§5.1.2`, `§5.1.5`, `§5.9`, `REQ-01`, `REQ-02`, `REQ-09`. `Preconditions:` `AF-00-02`. `Target Files:` `include/plugin_system.hpp`, `proto/capture.proto`, `src/aetherflow/core/shared_memory_layout.py`, `docs/breaking-changes/abi.md`, `docs/breaking-changes/proto.md`, `docs/breaking-changes/shmem.md`. `Behavior:` define the initial frozen contracts and their breaking-change ledgers only after the boundary/tooling checks pass. `Validation:` `uv run pytest tests/contracts/test_frozen_contracts.py -k frozen_contract_files_exist or test_breaking_change_logs_exist_for_frozen_contracts`. `Evidence:` all frozen files and ledgers exist together in one checkpoint. `ARP Trigger:` if any contract shape is still unstable, do not publish the freeze; capture the unresolved contract diff and stop.
- [ ] `AF-00-04` Create bounded sign-off packets for auth and bundle decisions. `PRD Refs:` `§5.10`, `§5.11.4`, `§10`, `REQ-10`, `REQ-11`. `Preconditions:` `AF-00-03`. `Target Files:` `docs/sign-offs/auth-provider.md`, `docs/sign-offs/bundle-format.md`, `docs/PLAN.md`. `Behavior:` define the decision deadline, blocking scope, and fallback path for auth-provider selection and bundle schema so downstream agents do not stall indefinitely. `Validation:` `uv run pytest tests/contracts/test_canonical_identity.py tests/contracts/test_frozen_contracts.py`. `Evidence:` each unresolved decision has an owner-independent fallback path and phase gate. `ARP Trigger:` if a sign-off item still has no fallback, mark the downstream item blocked explicitly in the plan before proceeding.

### Phase 0 Exit Criteria

```text
uv run ruff check .
uv run pytest tests/contracts
powershell -ExecutionPolicy Bypass -File scripts/build-native.ps1
```

## Phase 1 - Host Kernel, Trust, Entitlements, And Shell

- [ ] `AF-01-01` Build service container, plugin registry, trust verification, and catalog models. `PRD Refs:` `§4.1`, `§5.1.1-§5.1.4`, `REQ-02`. `Preconditions:` `AF-00-02`. `Target Files:` `src/aetherflow/core/services.py`, `src/aetherflow/plugins/manifest.py`, `src/aetherflow/plugins/registry.py`, `src/aetherflow/plugins/trust.py`, `src/aetherflow/plugins/catalog.py`. `Test Files:` `tests/unit/test_plugin_registry.py`, `tests/integration/test_signed_plugin_loading.py`. `Behavior:` discover plugins, verify signature + compatibility before load, block unsigned/tampered DLLs, and expose catalog metadata for locked/unlocked state. `Validation:` `uv run pytest tests/unit/test_plugin_registry.py tests/integration/test_signed_plugin_loading.py`. `Evidence:` signed plugins load, unsigned plugins fail before registration. `ARP Trigger:` capture failing manifest/signature payload and stop if unsigned execution is possible.
- [ ] `AF-01-02` Implement entitlement state machine, RBAC domain, and shell/status HUD skeleton. `PRD Refs:` `§3`, `§5.1.3-§5.1.5`, `§6`, `§7`, `REQ-02`, `REQ-03`, `REQ-07`. `Preconditions:` `AF-01-01`. `Target Files:` `src/aetherflow/core/entitlements.py`, `src/aetherflow/ui/shell.py`, `src/aetherflow/ui/router.py`, `src/aetherflow/ui/status_hud.py`, `src/aetherflow/ui/panels/plugin_catalog_panel.py`. `Test Files:` `tests/unit/test_entitlements.py`, `tests/integration/test_plugin_catalog_locking.py`, `tests/ui/test_status_hud.py`. `Behavior:` enforce LOADED/LOCKED/GRACE transitions, cache TTL, role-based visibility, and locked premium CTA flows in the UI shell. `Validation:` `uv run pytest tests/unit/test_entitlements.py tests/integration/test_plugin_catalog_locking.py tests/ui/test_status_hud.py`. `Evidence:` premium plugins never register UI/services unless entitled or in GRACE. `ARP Trigger:` if a locked premium plugin becomes selectable or loadable, stop and attach the entitlement trace.

### Phase 1 Exit Criteria

```text
uv run ruff check .
uv run pytest tests/unit/test_plugin_registry.py tests/unit/test_entitlements.py tests/integration/test_signed_plugin_loading.py tests/integration/test_plugin_catalog_locking.py tests/ui/test_status_hud.py
```

## Phase 2 - Controller Core, Input Layer, And Output Virtualization

- [ ] `AF-02-01` Deliver profiles, mapping pipeline, diagnostics, and baseline input plugins. `PRD Refs:` `§5.2`, `§5.6`, `REQ-04`, `REQ-08`. `Preconditions:` `AF-01-02`. `Target Files:` `src/aetherflow/core/profiles.py`, `src/aetherflow/input/xinput.py`, `src/aetherflow/input/playstation.py`, `src/aetherflow/input/kbm.py`, `src/aetherflow/core/diagnostics.py`. `Test Files:` `tests/unit/test_profiles.py`, `tests/integration/test_mapping_pipeline.py`, `tests/integration/test_input_plugins.py`. `Behavior:` create/clone/export/import profiles, fast switching, per-button mapping, curves/deadzones, translation hooks, and event-rate/latency metrics. `Validation:` `uv run pytest tests/unit/test_profiles.py tests/integration/test_mapping_pipeline.py tests/integration/test_input_plugins.py`. `Evidence:` profile CRUD and mapping pipeline pass deterministically across provider types. `ARP Trigger:` if latency sampling or provider normalization is nondeterministic, capture sample traces and halt.
- [ ] `AF-02-02` Add virtual output, masking service, and driver status/install UX. `PRD Refs:` `§5.3`, `§6`, `REQ-05`. `Preconditions:` `AF-02-01`. `Target Files:` `src/aetherflow/output/virtual_controller.py`, `src/aetherflow/output/device_masking.py`, `src/aetherflow/ui/panels/driver_status_panel.py`. `Test Files:` `tests/integration/test_output_virtualization.py`, `tests/ui/test_driver_panel.py`. `Behavior:` implement driver-backed output, optional masking, reversible install/repair actions, and clear status/error messaging. `Validation:` `uv run pytest tests/integration/test_output_virtualization.py tests/ui/test_driver_panel.py`. `Evidence:` double-input prevention is controllable and UI repair flows are testable. `ARP Trigger:` if output requires unsigned artifacts or irreversible system changes, stop and document the blocker.

### Phase 2 Exit Criteria

```text
uv run ruff check .
uv run pytest tests/unit/test_profiles.py tests/integration/test_mapping_pipeline.py tests/integration/test_input_plugins.py tests/integration/test_output_virtualization.py tests/ui/test_driver_panel.py
```

## Phase 3 - Capture And Display Plugin Stack

- [ ] `AF-03-01` Implement OpenCV capture, device enumeration, mode matrix, and OBS fixed plugin. `PRD Refs:` `§5.4.1`, `§5.4.2`, `§5.4.4`, `§5.4.5`, `REQ-06`. `Preconditions:` `AF-01-02`, `AF-02-01`. `Target Files:` `src/aetherflow/vision/opencv_capture.py`, `src/aetherflow/vision/obs_capture.py`, `src/aetherflow/ui/panels/capture_panel.py`, `src/aetherflow/core/capture_metrics.py`. `Test Files:` `tests/integration/test_capture_opencv.py`, `tests/ui/test_capture_mode_matrix.py`, `tests/integration/test_capture_stability.py`. `Behavior:` enumerate runtime devices with stable IDs, expose only supported FPS/resolution combinations, surface measured FPS/drops/jitter, and keep OBS as fixed-config start/stop behavior. `Validation:` `uv run pytest tests/integration/test_capture_opencv.py tests/ui/test_capture_mode_matrix.py tests/integration/test_capture_stability.py`. `Evidence:` unsupported combinations are hidden/disabled with reasons; diagnostics exportable. `ARP Trigger:` if measured FPS or mode support cannot be derived deterministically from device state, capture hardware metadata and stop.
- [ ] `AF-03-02` Add premium MF/DS capture plugins, CPU/GPU render modes, and fallback UX. `PRD Refs:` `§5.4.3`, `§5.5`, `§6`, `§7`, `REQ-02`, `REQ-06`, `REQ-07`. `Preconditions:` `AF-03-01`. `Target Files:` `src/aetherflow/vision/mf_capture.py`, `src/aetherflow/vision/ds_capture.py`, `src/aetherflow/ui/panels/render_mode_panel.py`, `src/aetherflow/ui/panels/capture_diagnostics_panel.py`. `Test Files:` `tests/integration/test_capture_premium_gating.py`, `tests/ui/test_render_modes.py`, `tests/ui/test_capture_fallback_actions.py`. `Behavior:` register MF/DS backends only when entitled, expose format dropdown for unlocked premium plugins, and deliver CPU/GPU render panels plus one-click fallback recommendations. `Validation:` `uv run pytest tests/integration/test_capture_premium_gating.py tests/ui/test_render_modes.py tests/ui/test_capture_fallback_actions.py`. `Evidence:` locked premium plugins never expose providers/panels; render modes surface correct latency/performance tradeoffs. `ARP Trigger:` if premium backends appear in selectors without entitlement, stop and attach the registry snapshot.

### Phase 3 Exit Criteria

```text
uv run ruff check .
uv run pytest tests/integration/test_capture_opencv.py tests/ui/test_capture_mode_matrix.py tests/integration/test_capture_stability.py tests/integration/test_capture_premium_gating.py tests/ui/test_render_modes.py tests/ui/test_capture_fallback_actions.py
```

## Phase 4 - Worker Supervision And Environment Management

- [ ] `AF-04-01` Implement worker supervisor, gRPC control plane, shared-memory ring, and health/log UI. `PRD Refs:` `§5.1.5`, `§5.9`, `REQ-09`. `Preconditions:` `AF-00-02`, `AF-03-01`. `Target Files:` `src/aetherflow/core/ipc/`, `src/aetherflow/core/worker_supervisor.py`, `src/aetherflow/core/shared_memory_layout.py`, `src/aetherflow/ui/panels/worker_health_panel.py`. `Test Files:` `tests/integration/test_worker_supervisor.py`, `tests/stress/test_worker_crash_loop.py`. `Behavior:` start/stop/restart workers, track heartbeats, apply bounded backoff, transport frames via shared memory, and surface logs/health in UI. `Validation:` `uv run pytest tests/integration/test_worker_supervisor.py tests/stress/test_worker_crash_loop.py`. `Evidence:` host survives worker crashes and restarts within policy. `ARP Trigger:` if host death or worker unrecoverable loops occur, collect supervisor logs and crash dumps before retrying.
- [ ] `AF-04-02` Deliver environment manager UX and bundle install workflow behind sign-off gates. `PRD Refs:` `§5.10`, `REQ-10`. `Preconditions:` `AF-04-01`, Phase-0 bundle sign-off. `Target Files:` `src/aetherflow/core/env_manager.py`, `src/aetherflow/core/bundle_installer.py`, `src/aetherflow/ui/panels/environment_panel.py`. `Test Files:` `tests/unit/test_env_manager.py`, `tests/test_bundle_installer.py`. `Behavior:` create/repair/recreate/delete envs, show metadata/validation state, and install signed one-click bundles with streamed logs and repair options. `Validation:` `uv run pytest tests/unit/test_env_manager.py tests/test_bundle_installer.py`. `Evidence:` env state and bundle install outcomes are machine-verifiable. `ARP Trigger:` if bundle signature, hash, or import validation fails, capture manifest, logs, and failing import list; do not auto-bypass.

### Phase 4 Exit Criteria

```text
uv run ruff check .
uv run pytest tests/integration/test_worker_supervisor.py tests/stress/test_worker_crash_loop.py tests/unit/test_env_manager.py tests/test_bundle_installer.py
```

## Phase 5 - Online Resources, Admin, Packaging, And Evidence

- [ ] `AF-05-01` Build signed Online Resources client and install surfaces. `PRD Refs:` `§5.11.1`, `§5.11.2`, `§5.11.4`, `§6`, `REQ-11`. `Preconditions:` `AF-01-02`, `AF-04-02`, auth sign-off. `Target Files:` `src/aetherflow/core/resources_manifest.py`, `src/aetherflow/core/resources_client.py`, `src/aetherflow/ui/panels/resources_panel.py`, `src/aetherflow/ui/panels/resource_details_modal.py`. `Test Files:` `tests/integration/test_resources_manifest.py`, `tests/ui/test_resource_details_modal.py`, `tests/test_security.py`. `Behavior:` fetch and verify signed manifests, display metadata/lock state, support one-click install for scripts/profiles/models/bundles, and keep auth provider integration abstract until provider sign-off lands. `Validation:` `uv run pytest tests/integration/test_resources_manifest.py tests/ui/test_resource_details_modal.py tests/test_security.py`. `Evidence:` unsigned or tampered resources never install; premium resources show required tier/add-on. `ARP Trigger:` if trust-root validation or premium lock state is bypassed, stop and capture manifest/signature chain.
- [ ] `AF-05-02` Implement admin/operator surfaces, Windows packaging/update flows, diagnostics export, and success-metric collectors. `PRD Refs:` `§5.12`, `§7`, `§8`, `§9`, `REQ-03`, `REQ-12`, `REQ-13`. `Preconditions:` `AF-05-01`. `Target Files:` `src/aetherflow/ui/panels/admin_panel.py`, `src/aetherflow/core/audit_log.py`, `src/aetherflow/core/diagnostics_export.py`, `scripts/package-windows.ps1`, `scripts/run-e2e.ps1`. `Test Files:` `tests/integration/test_admin_dashboard.py`, `tests/integration/test_diagnostics_export.py`, `tests/e2e/test_onboarding_timing.py`. `Behavior:` deliver user/role/entitlement/session management with audit trails, package the Windows runtime, support staged update/rollback, and produce the evidence artifacts named in `PRD-§9`. `Validation:` `uv run pytest tests/integration/test_admin_dashboard.py tests/integration/test_diagnostics_export.py tests/e2e/test_onboarding_timing.py`. `Evidence:` `logs/onboarding_timing.json`, `logs/bundle_install_report.json`, `logs/survivability_report.json`, `logs/capture_stability.json`, `logs/entitlement_gate_report.json`, `logs/security_audit.json`. `ARP Trigger:` if evidence artifacts are missing or packaging breaks rollback guarantees, capture script logs and block release.

### Phase 5 Exit Criteria

```text
uv run ruff check .
uv run pytest
powershell -ExecutionPolicy Bypass -File scripts/package-windows.ps1
```

## Risk Register

| ID | Area | Description | Mitigation | Related Items |
| --- | --- | --- | --- | --- |
| `RISK-01` | Canonical paths | Stale `Aetherlink` references cause implementation in the wrong package tree | Canonicalize first and add contract tests | `AF-00-01` |
| `RISK-02` | Tooling | Windows/WSL execution mismatch prevents `uv` and native build reproducibility | Separate environment verification from contract freezing and gate the freeze on a passing harness check | `AF-00-02` |
| `RISK-03` | Contract churn | ABI/proto/shmem changes after downstream work create cascading rework | Freeze contracts only after boundary/tooling verification and keep dedicated breaking-change logs | `AF-00-03` |
| `RISK-04` | Security/Entitlements | Premium or unsigned artifacts become reachable before enforcement is complete | Implement trust verification and entitlement gating before feature plugins | `AF-01-01`, `AF-01-02`, `AF-05-01` |

## Traceability Matrix

| PRD Section | Requirement IDs | Work Item IDs | Status |
| --- | --- | --- | --- |
| `§1`, `G3`, `§4.1-§4.5` | `REQ-01` | `AF-00-01`, `AF-00-02`, `AF-00-03`, `AF-01-01` | Planned |
| `§2.1` | `REQ-02`, `REQ-10`, `REQ-11` | `AF-01-01`, `AF-04-02`, `AF-05-01` | Planned |
| `§2.2` | `REQ-14` | `AF-00-01` | Planned |
| `§3` | `REQ-03`, `REQ-12` | `AF-01-02`, `AF-05-02` | Planned |
| `§5.1` | `REQ-02` | `AF-00-03`, `AF-01-01`, `AF-01-02`, `AF-03-02` | Planned |
| `§5.2` | `REQ-04` | `AF-02-01` | Planned |
| `§5.3` | `REQ-05` | `AF-02-02` | Planned |
| `§5.4` | `REQ-06` | `AF-03-01`, `AF-03-02` | Planned |
| `§5.5`, `§6` | `REQ-07` | `AF-01-02`, `AF-03-02` | Planned |
| `§5.6` | `REQ-08` | `AF-02-01` | Planned |
| `§5.9` | `REQ-09` | `AF-00-03`, `AF-04-01` | Planned |
| `§5.10` | `REQ-10` | `AF-04-02` | Planned |
| `§5.11.1`, `§5.11.2`, `§5.11.4` | `REQ-11` | `AF-05-01` | Planned |
| `§5.12`, `§7` | `REQ-03`, `REQ-12` | `AF-01-02`, `AF-05-02` | Planned |
| `§8`, `§9` | `REQ-13` | `AF-05-02` | Planned |
| `§10` | `ASM-04`, `ASM-05` | `AF-00-04`, `AF-04-02`, `AF-05-01` | Planned |
| `§5.7`, `§5.8.1`, `§5.8.2`, `§5.11.3` | none | none | Deferred by scope |

## Next Recommended Implementation Order

1. Start with `AF-00-01` to remove stale project identity/path ambiguity.
2. Execute `AF-00-02`, `AF-00-03`, and `AF-00-04` in order so the native boundary, frozen contracts, and unresolved-decision fallbacks are all explicit before feature work.
3. Move to `AF-01-01` and `AF-01-02`; no device, capture, worker, or resource work should begin before trust and entitlement gates exist.
