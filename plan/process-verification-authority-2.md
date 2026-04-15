---
goal: Integrate root PLAN gap-closure work into the current repo and replace weak verification assumptions with a single authoritative proof model
version: 2.0
date_created: 2026-03-27
last_updated: 2026-03-27
owner: Codex
status: Planned
tags: [process, verification, architecture, migration, tooling]
---

# Introduction

![Status: Planned](https://img.shields.io/badge/status-Planned-blue)

This implementation plan integrates the root `PLAN.md` into the current
repository by treating `docs/PLAN.md` as the canonical implementation plan,
rewriting root `PLAN.md` as a strict gap-closure and verifier-hardening plan,
and defining a single authoritative verification path. The updated model
rejects heuristic sweeps, report generation, and evidence-file presence as
proof of real functionality. A feature becomes `verified` only when executable
proof tied to acceptance criteria passes through the intended entry point,
includes relevant failure coverage, and has approved reviewer sign-off.
Performance-sensitive claims require explicit performance artifacts and
thresholds.

## 1. Requirements & Constraints

- **REQ-001**: `docs/PLAN.md` remains the canonical implementation plan
  referenced by repo docs and automation.
- **REQ-002**: Root `PLAN.md` becomes the current-state gap-closure and
  verifier-hardening plan only.
- **REQ-003**: Adopt a single authoritative verification model:
  - Canonical evaluator: `src/aetherflow/core/verification_report.py`
  - Canonical regrade/report command:
    `uv run python -m tools.verify_requirements`
  - Canonical outputs: `docs/requirements-report.md` and
    `logs/verification/*.json`
- **REQ-004**: `tools/generate_verification_report.py` must be documented as a
  compatibility wrapper or deprecated helper, not a second source of truth.
- **REQ-005**: `tools/audit_plan_completion.py` must be explicitly documented as
  advisory only and must never contribute to `coded`, `evidenced`, or
  `verified` status.
- **REQ-006**: A work item may not be considered functionally verified from file
  existence, report generation, evidence-pack presence, parser sweeps,
  grep/path heuristics, broad smoke tests, or reviewer intuition without
  executable proof.
- **REQ-007**: Verification requires acceptance-criteria coverage, entry-point
  coverage, negative-path coverage where relevant, successful validations, and
  reviewer approval.
- **REQ-008**: Performance-sensitive claims such as KBM, capture, latency, or
  throughput must not be marked “performant” without explicit benchmark or
  telemetry artifacts tied to thresholds.
- **REQ-009**: The integrated plan must identify and close the current
  unresolved gaps shown by `docs/requirements-report.md`, not re-plan already
  shipped infrastructure.
- **REQ-010**: Follow the `update-implementation-plan` structure for the
  machine-readable implementation spec.
- **REQ-011**: Follow `docs/dev/generate-tasks.md` for the execution checklist.
- **CON-001**: Do not change frozen contracts, generated gRPC stubs, or
  entitlement semantics as part of planning integration.
- **CON-002**: The repo currently contains overlapping verification tools and
  stale references; the plan must normalize them to current `tools/` and
  `scripts/` entrypoints.
- **CON-003**: Existing evidence packs and verification JSONs may be
  structurally valid while still being insufficient as proof of real
  functionality.
- **PAT-001**: One authoritative verifier, one authoritative report path, and
  advisory tools clearly labeled.

## 2. Implementation Steps

### Implementation Phase 1

- **GOAL-001**: Re-baseline planning authority and normalize the repo’s
  verification architecture.

<!-- prettier-ignore-start -->
| Task     | Description                                                                                                                                                                                                                                                                                    | Completed | Date |
|----------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------|------|
| TASK-001 | Rewrite root `PLAN.md` so it no longer proposes building already-shipped verification infrastructure and instead defines the remaining gap-closure and hardening work.                                                                                                                         |           |      |
| TASK-002 | Add a “Current Implemented State” section to root `PLAN.md` listing shipped components: `docs/verification_standard.md`, `docs/PLAN.md` metadata, `docs/evidence/`, `logs/verification/`, `tools/proof_verifier.py`, `tools/verify_requirements.py`, app-check persistence, and current tests. |           |      |
| TASK-003 | Add a “Verification Authority Model” section to root `PLAN.md` that declares `uv run python -m tools.verify_requirements` as the canonical regrade/report path.                                                                                                                                |           |      |
| TASK-004 | Document `tools/generate_verification_report.py` as a wrapper around the canonical model and document whether it remains for compatibility or is slated for deprecation.                                                                                                                       |           |      |
| TASK-005 | Document `tools/audit_plan_completion.py` as non-authoritative and heuristic, with explicit language that it cannot prove functionality or drive status promotion.                                                                                                                             |           |      |
<!-- prettier-ignore-end -->

### Implementation Phase 2

- **GOAL-002**: Tighten the proof model so `verified` means real functionality,
  not document completeness.

<!-- prettier-ignore-start -->
| Task     | Description                                                                                                                                                                                                                              | Completed | Date |
|----------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------|------|
| TASK-006 | Update root `PLAN.md` to define `verified` as explicit AC coverage, executable proof through the intended entry point, required failure-path coverage, successful validations, approved reviewer sign-off, and no unresolved proof gaps. |           |      |
| TASK-007 | Add explicit language that `docs/evidence/<item>.md` and `logs/verification/<item>.json` are evidence indexes and reviewer artifacts, not proof by themselves.                                                                           |           |      |
| TASK-008 | Define the required proof classes by feature type: `logic`, `service`, `ui`, `boundary`, `workflow`, and add a separate proof requirement for performance-sensitive items.                                                               |           |      |
| TASK-009 | Define performance verification rules in root `PLAN.md`: performance claims require thresholded artifacts such as latency telemetry, frame-drop logs, throughput measurements, or benchmark outputs tied to the item’s ACs.              |           |      |
| TASK-010 | Update the evidence-pack contract to require explicit linkage between each AC and its exact proof artifact, not just a referenced test filename.                                                                                         |           |      |
| TASK-011 | Update the verification JSON contract to record, per item, AC coverage, proof gaps, validation outcomes, reviewer state, app-check state, and performance-proof state when applicable.                                                   |           |      |
<!-- prettier-ignore-end -->

### Implementation Phase 3

- **GOAL-003**: Remove ambiguity from plan metadata and eliminate hidden
  verifier defaults.

<!-- prettier-ignore-start -->
| Task     | Description                                                                                                                                                                                                                                                                                                                                        | Completed | Date |
|----------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------|------|
| TASK-012 | Define the canonical metadata keys required in `docs/PLAN.md` for every active `AF-*` item: `Lifecycle`, `Feature-Class`, `Entry-Point`, `Acceptance Criteria`, `Required-Proof-Types`, `Required-Failure-Modes`, `Evidence-Pack`, `Validation`, `App-Testable`, `App-Surface`, `Developer-Alert-Message`, and `Performance-Claim` where relevant. |           |      |
| TASK-013 | Audit `src/aetherflow/core/verification_report.py` and identify every place where repo defaults are currently hardcoded instead of sourced from plan metadata.                                                                                                                                                                                     |           |      |
| TASK-014 | Update root `PLAN.md` to require migration of active-item defaults out of code and into `docs/PLAN.md`, keeping code defaults only as temporary backward-compatibility behavior during migration.                                                                                                                                                  |           |      |
| TASK-015 | Add a compatibility section documenting how legacy evidence packs and legacy verification JSONs are handled during migration and regrade.                                                                                                                                                                                                          |           |      |
| TASK-016 | Define stale-evidence rules: when validations, proof artifacts, or metrics are outdated relative to the implementation, the item must degrade from `verified` to `evidenced`.                                                                                                                                                                      |           |      |
<!-- prettier-ignore-end -->

### Implementation Phase 4

- **GOAL-004**: Turn the current report into a deterministic closure matrix for
  remaining work.

<!-- prettier-ignore-start -->
| Task     | Description                                                                                                                                                                                                                                                                       | Completed | Date |
|----------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------|------|
| TASK-017 | Add a “Closure Matrix” to root `PLAN.md` keyed by each non-verified `AF-*` item currently listed in `docs/requirements-report.md`.                                                                                                                                                |           |      |
| TASK-018 | For each `AF-*` item, classify the remaining work as one or more of: `metadata gap`, `evidence-pack gap`, `AC coverage gap`, `failure-coverage gap`, `validation gap`, `review/sign-off gap`, or `performance-proof gap`.                                                         |           |      |
| TASK-019 | For each `AF-*` item, specify the exact closure action and affected file class: `docs/PLAN.md`, `docs/evidence/<item>.md`, verifier/report code, or reviewer-only action.                                                                                                         |           |      |
| TASK-020 | Explicitly exclude already-shipped infrastructure tasks from the closure matrix so execution work targets only real remaining gaps.                                                                                                                                               |           |      |
| TASK-021 | Add integrated completion criteria to root `PLAN.md`: no active item remains blocked by undocumented metadata, no active item remains “verified” from weak evidence, and all performance-sensitive claims are either artifact-backed or explicitly downgraded to functional-only. |           |      |
<!-- prettier-ignore-end -->

### Implementation Phase 5

- **GOAL-005**: Resolve developer-alert semantics so alerts do not pretend to
  prove functionality.

<!-- prettier-ignore-start -->
| Task     | Description                                                                                                                                                                                                                                                                             | Completed | Date |
|----------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------|------|
| TASK-022 | Update root `PLAN.md` to state that app-check alerts are prompts for human inspection only and never contribute to verification status.                                                                                                                                                 |           |      |
| TASK-023 | Define authoritative acknowledgement behavior for pending app checks. Current startup logic in `src/aetherflow/main.py` auto-acknowledges after loading; the integrated plan must either codify that as intended behavior or replace it with explicit manual acknowledgement semantics. |           |      |
| TASK-024 | Define the required persistent alert fields: `item_id`, `message`, `app_surface`, `evidence_pack`, `status`, `created_at`, and acknowledgement state if retained.                                                                                                                       |           |      |
| TASK-025 | Require test updates if alert semantics change, covering startup loading, deduplication, acknowledgement, and non-authoritative status.                                                                                                                                                 |           |      |
<!-- prettier-ignore-end -->

### Implementation Phase 6

- **GOAL-006**: Publish the execution checklist in `tasks/` using the repo’s
  generate-tasks model, with `tasks/tasks-rework-plan.md` as the execution
  handoff for this plan.

<!-- prettier-ignore-start -->
| Task     | Description                                                                                                                               | Completed | Date |
|----------|-------------------------------------------------------------------------------------------------------------------------------------------|-----------|------|
| TASK-026 | Update `tasks/tasks-rework-plan.md` so it serves as the execution handoff for this plan’s verification-authority gap-closure work.       |           |      |
| TASK-027 | Replace the current literal sentence-decomposition style in `tasks/tasks-rework-plan.md` with the final execution checklist for this plan. |           |      |
| TASK-028 | Include `0.0 Create feature branch` unless the user later suppresses it.                                                                  |           |      |
<!-- prettier-ignore-end -->

## 3. Alternatives

- **ALT-001**: Keep multiple report generators as equal authorities. Rejected
  because conflicting “truth” sources are the core problem.
- **ALT-002**: Treat evidence packs and verification JSONs as sufficient proof
  once syntactically complete. Rejected because this still allows false
  confidence about real functionality.
- **ALT-003**: Preserve heuristic auditors as status drivers. Rejected because
  `audit_plan_completion.py` is path/grep/validation based and cannot prove
  end-user behavior.
- **ALT-004**: Allow reviewer discretion to approve performance-sensitive items
  without artifacts. Rejected because performance claims must be independently
  proven.

## 4. Dependencies

- **DEP-001**: `docs/PLAN.md` as canonical implementation plan.
- **DEP-002**: `PLAN.md` as rewritten gap-closure and verifier-hardening plan.
- **DEP-003**: `tools/verify_requirements.py` as canonical command entrypoint.
- **DEP-004**: `tools/proof_verifier.py` and
  `src/aetherflow/core/verification_report.py` as canonical evaluation and
  reporting path.
- **DEP-005**: `docs/requirements-report.md` as the unresolved-gap baseline.
- **DEP-006**: `docs/evidence/*.md` and `logs/verification/*.json` as
  structured evidence records only.
- **DEP-007**: `src/aetherflow/core/developer_app_checks.py` and
  `src/aetherflow/main.py` for app-check semantics.
- **DEP-008**: `docs/dev/generate-tasks.md` for the `tasks/` artifact shape.

## 5. Files

- **FILE-001**: `PLAN.md` - Rewrite as the strict gap-closure and
  verifier-hardening plan.
- **FILE-002**: `docs/PLAN.md` - Canonical implementation plan; update only if
  metadata or item definitions must be strengthened.
- **FILE-003**: `plan/process-verification-authority-2.md` - Machine-readable
  implementation spec.
- **FILE-004**: `tasks/tasks-verification-authority-gap-closure.md` - New
  execution handoff.
- **FILE-005**: `tasks/tasks-rework-plan.md` - Deprecation pointer after the new
  task file exists.
- **FILE-006**: `docs/requirements-report.md` - Baseline for closure matrix and
  gap tracking.
- **FILE-007**: `docs/verify-requirements-pipeline.md` - Workflow description
  alignment target.
- **FILE-008**: `tools/verify_requirements.py` - Canonical command entrypoint
  documentation target.
- **FILE-009**: `tools/generate_verification_report.py` - Wrapper/deprecation
  decision target.
- **FILE-010**: `tools/audit_plan_completion.py` - Advisory-only classification
  target.
- **FILE-011**: `src/aetherflow/core/verification_report.py` - Metadata/default
  and JSON-contract implementation target.
- **FILE-012**: `src/aetherflow/main.py` - App-check acknowledgement semantics
  target.

## 6. Testing

- **TEST-001**: Re-run `tests/contracts/test_plan_metadata.py` after any
  `docs/PLAN.md` metadata changes.
- **TEST-002**: Re-run `tests/contracts/test_verification_reporting.py` after
  any report or JSON contract changes.
- **TEST-003**: Add or update contract tests to ensure non-authoritative tools
  cannot claim or promote `verified`.
- **TEST-004**: Add or update tests so performance-sensitive items cannot be
  marked performance-verified without explicit artifacts and thresholds.
- **TEST-005**: Add or update tests so stale evidence or stale performance
  artifacts degrade item state.
- **TEST-006**: Re-run `tests/unit/test_developer_app_checks.py` and
  `tests/e2e/test_verification_chain.py` if alert semantics change.

## 7. Risks & Assumptions

- **RISK-001**: Leaving overlapping tools ambiguous will preserve false
  confidence and future drift.
- **RISK-002**: Treating evidence artifacts as proof can still let unverified
  functionality appear complete.
- **RISK-003**: Performance claims are the easiest place for false positives
  unless artifacts and thresholds are required.
- **RISK-004**: Removing code defaults too aggressively could break backward
  compatibility for legacy evidence packs.
- **RISK-005**: Changing alert acknowledgement semantics without updating tests
  will create silent behavioral drift.
- **ASSUMPTION-001**: The repo should use a strict executable proof bar.
- **ASSUMPTION-002**: The repo should use one authoritative verification path
  and classify all other tools as wrapper or advisory.
- **ASSUMPTION-003**: Performance-sensitive claims must be independently proven,
  not inferred from functionality tests.

## 8. Related Specifications / Further Reading

- `docs/PLAN.md`
- `PLAN.md`
- `docs/requirements-report.md`
- `docs/verify-requirements-pipeline.md`
- `tools/verify_requirements.py`
- `tools/generate_verification_report.py`
- `tools/proof_verifier.py`
- `tools/audit_plan_completion.py`
- `src/aetherflow/core/verification_report.py`
- `src/aetherflow/core/developer_app_checks.py`
- `src/aetherflow/main.py`
- `docs/dev/generate-tasks.md`
