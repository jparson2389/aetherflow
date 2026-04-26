# Branch Worktree Stabilization Inventory

## Run Context

- Date: April 26, 2026
- Branch: `chore/master-infra-alignment`
- Purpose: Preserve the messy worktree while grouping changes into reviewable
  stabilization slices.

## Validation Environment

Use the explicit local `uv` path and writable cache until the shell `PATH` is
normalized:

```text
env PATH=/home/auto_23/.local/bin:$PATH UV_CACHE_DIR=/tmp/aetherflow-uv-cache /home/auto_23/.local/bin/uv ...
```

## Worktree Groups

### Group A: Runtime Authority And Delivery Layout Docs

- `AGENTS.md`
- `CLAUDE.md`
- `README.md`
- `docs/PLAN.md`
- `docs/PRD.md`
- `docs/architecture/delivery-architecture-alignment-notes.md`
- `docs/architecture/delivery-runtime-layout.md`
- `docs/architecture/runtime-authority-decision.md`
- `docs/automation-loop/README.md`
- `docs/evidence/task-1-runtime-authority-alignment.md`
- `tests/contracts/test_delivery_architecture_alignment.py`

Validation:

- `uv run pytest tests/contracts/test_delivery_architecture_alignment.py`
- `uv run pytest tests/contracts/`

### Group B: Native Host Supervisor Scaffold

- `host/native_harness.cpp`
- `host/supervisor.cpp`
- `include/supervisor.hpp`

Validation:

- `uv run pytest tests/contracts/test_native_harness.py`
- Windows-only native harness tests may skip on non-Windows hosts.

### Group C: Python Host-State View

- `src/aetherflow/core/worker_supervisor.py`
- `tests/integration/test_worker_supervisor.py`
- `tests/integration/test_host_supervision_model.py`
- `tests/stress/test_worker_crash_loop.py`

Validation:

- `uv run pytest tests/integration/test_worker_supervisor.py tests/integration/test_host_supervision_model.py tests/stress/test_worker_crash_loop.py`

### Group D: Verification, Reporting, And Automation Loop Hardening

- `src/aetherflow/core/verification_report.py`
- `tests/contracts/test_evidence_packs.py`
- `tests/contracts/test_plan_exec_recovery.py`
- `tests/contracts/test_plan_metadata.py`
- `tests/contracts/test_proof_verifier.py`
- `tests/contracts/test_regrade.py`
- `tests/contracts/test_verification_reporting.py`
- `tests/contracts/test_verification_standard.py`
- `tests/e2e/test_verification_chain.py`
- `tests/unit/test_check_quality.py`
- `tests/unit/test_developer_app_checks.py`
- `tests/unit/test_verify_requirements.py`
- `tools/apply_writes.py`
- `tools/plan_exec.py`

Validation:

- `uv run python -m tools.verify_requirements`
- `uv run pytest tests/contracts/test_plan_exec_recovery.py tests/contracts/test_regrade.py tests/contracts/test_proof_verifier.py tests/e2e/test_verification_chain.py`

### Group E: Formatting, Path Cleanup, Assets, And Miscellaneous Drift

- `.gitattributes`
- `assets/diagrams/delivery-runtime-layout.svg`
- `assets/architecture/delivery-runtime-layout.png`
- `docs/delivery-runtime-layout.md`
- `logs/quality-gate.log`
- `src/aetherflow/core/entitlements.py`
- `src/aetherflow/core/profile_persistence.py`
- `src/aetherflow/core/settings.py`
- `src/aetherflow/plugins/trust.py`
- `src/aetherflow/security/manifest_signing.py`
- `tests/contracts/test_env_readiness.py`
- `tests/unit/test_kbm_plugin.py`
- `tests/unit/test_security_report_summary_skill.py`
- `tools/build_assets.py`
- `tools/export_diagrams.py`

Disposition:

- Leave `docs/delivery-runtime-layout.md` unstaged; canonical references should
  use `docs/architecture/delivery-runtime-layout.md`.
- Stage generated assets only when a canonical doc or test references them.
- Keep logs unstaged unless they are intentionally used as evidence.

## Current Blocker Policy

- Do not promote `AF-04-01` to `verified`; the canonical requirements report
  still records `Entry point not exercised: host worker supervisor` and
  reviewer sign-off is pending.
- Treat `state/plan_state.json` as advisory until reconcile-only output matches
  `docs/requirements-report.md`.
- Do not add new feature work until Ruff, targeted contracts, canonical regrade,
  and the full suite have been run against grouped changes.
