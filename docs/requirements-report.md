# Requirements Report

## Summary
- Retired: 1
- Drafted: 0
- Coded: 0
- Evidenced: 7
- Verified: 8
- Complete: 0

## Coverage by Plan Item

### AF-00-01 - Canonicalize repo identity and self-contained docs.
- Status: retired
- Evidence Pack: docs/evidence/AF-00-01.md
- Validation: uv run pytest tests/contracts/test_canonical_identity.py::test_canonical_package_root_is_aetherflow tests/contracts/test_canonical_identity.py::test_project_docs_reference_aetherflow_canonical_paths tests/contracts/test_prd_execution_readiness.py::test_prd_is_self_contained_and_citation_free

### AF-00-02a - Verify Windows toolchain and `uv` environment.
- Status: verified
- Evidence Pack: docs/evidence/AF-00-02a.md
- Validation: uv run pytest tests/contracts/test_env_readiness.py
- Reviewer: qa.lead

### AF-00-02b - Establish native boundary and build harness.
- Status: evidenced
- Gaps: Validation failed: powershell -ExecutionPolicy Bypass -File scripts/build-native.ps1
- Evidence Pack: docs/evidence/AF-00-02b.md
- Validation: powershell -ExecutionPolicy Bypass -File scripts/build-native.ps1

### AF-00-03 - Publish control-plane proto surface and shared-memory ring semantics.
- Status: verified
- Evidence Pack: docs/evidence/AF-00-03.md
- Validation: uv run pytest tests/contracts/test_execution_contracts.py -k "proto or overflow"
- Reviewer: qa.lead

### AF-00-04 - Publish signing and runtime-state ABI, then freeze contracts.
- Status: verified
- Evidence Pack: docs/evidence/AF-00-04.md
- Validation: uv run pytest tests/contracts/test_execution_contracts.py tests/contracts/test_frozen_contracts.py
- Reviewer: qa.lead

### AF-00-05 - Publish bounded sign-off packets and failure-UX state model.
- Status: verified
- Evidence Pack: docs/evidence/AF-00-05.md
- Validation: uv run pytest tests/contracts/test_prd_execution_readiness.py -k plan
- Reviewer: qa.lead

### AF-01-01 - Implement trust verification and plugin/resource catalog policy.
- Status: verified
- Evidence Pack: docs/evidence/AF-01-01.md
- Validation: uv run pytest tests/unit/test_plugin_registry.py tests/integration/test_signed_plugin_loading.py tests/test_security.py
- Reviewer: qa.lead

### AF-01-02 - Implement entitlement runtime states and shell-safe degradation model.
- Status: verified
- Evidence Pack: docs/evidence/AF-01-02.md
- Validation: uv run pytest tests/unit/test_entitlements.py tests/integration/test_plugin_catalog_locking.py tests/ui/test_status_hud.py
- Reviewer: qa.lead
- App-Testable: yes
- App Surface: status-hud

### AF-02-01 - Deliver profiles, mapping, translation, diagnostics, and input plugins.
- Status: evidenced
- Gaps: Reviewer sign-off is not approved
- Evidence Pack: docs/evidence/AF-02-01.md
- Validation: uv run pytest tests/unit/test_profiles.py tests/integration/test_mapping_pipeline.py tests/integration/test_input_plugins.py

### AF-02-02 - Add virtual output, masking, and plugin-failure-safe output UX.
- Status: verified
- Evidence Pack: docs/evidence/AF-02-02.md
- Validation: uv run pytest tests/integration/test_output_virtualization.py tests/ui/test_driver_panel.py
- Reviewer: qa.lead
- App-Testable: yes
- App Surface: driver-status-panel

### AF-03-01 - Implement OpenCV capture, mode matrix enforcement, and 60 FPS baseline validation.
- Status: evidenced
- Gaps: Reviewer sign-off is not approved
- Evidence Pack: docs/evidence/AF-03-01.md
- Validation: uv run pytest tests/integration/test_capture_opencv.py tests/ui/test_capture_mode_matrix.py tests/integration/test_capture_stability.py

### AF-03-02 - Add premium capture backends, CPU/GPU render modes, and one validated 120 FPS path.
- Status: evidenced
- Gaps: Reviewer sign-off is not approved
- Evidence Pack: docs/evidence/AF-03-02.md
- Validation: uv run pytest tests/integration/test_capture_premium_gating.py tests/ui/test_render_modes.py tests/ui/test_capture_fallback_actions.py tests/integration/test_capture_120fps_path.py

### AF-04-01 - Implement worker supervision with restart ceilings and escalation UX.
- Status: evidenced
- Gaps: Reviewer sign-off is not approved
- Evidence Pack: docs/evidence/AF-04-01.md
- Validation: uv run pytest tests/integration/test_worker_supervisor.py tests/stress/test_worker_crash_loop.py

### AF-04-02 - Deliver environment manager and bounded bundle validation workflow.
- Status: verified
- Evidence Pack: docs/evidence/AF-04-02.md
- Validation: uv run pytest tests/unit/test_env_manager.py tests/test_bundle_installer.py
- Reviewer: qa.lead
- App-Testable: yes
- App Surface: environment-panel

### AF-05-01 - Build Online Resources trust flow with mock-provider fallback.
- Status: evidenced
- Gaps: Reviewer sign-off is not approved
- Evidence Pack: docs/evidence/AF-05-01.md
- Validation: uv run pytest tests/integration/test_resources_manifest.py tests/ui/test_resource_details_modal.py tests/test_security.py

### AF-05-02 - Implement admin, diagnostics export, packaging, and evidence collectors.
- Status: evidenced
- Gaps: Reviewer sign-off is not approved
- Evidence Pack: docs/evidence/AF-05-02.md
- Validation: uv run pytest tests/integration/test_admin_dashboard.py tests/integration/test_diagnostics_export.py tests/e2e/test_onboarding_timing.py
