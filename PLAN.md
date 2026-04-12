# Verification Authority Gap-Closure Plan

## Summary

The repository already contains a substantial evidence-based verification
system:

- `docs/verification_standard.md`
- `docs/PLAN.md`
- `docs/evidence/<item-id>.md`
- `logs/verification/<item-id>.json`
- `tools/verify_requirements.py`
- `tools/proof_verifier.py`
- `tools/generate_verification_report.py`
- `src/aetherflow/core/verification_report.py`
- `src/aetherflow/core/developer_app_checks.py`

The remaining problem is trust, not absence. The repo has multiple overlapping
tools that can produce reports, indexes, and status files, but those outputs are
not safe to treat as proof that a feature is truly functional or performant.

This root plan is therefore no longer a rewrite-from-scratch plan. It is the
current-state gap-closure plan for making verification trustworthy, reducing
tooling ambiguity, and turning the remaining report gaps into explicit closure
work.

## Current Implemented State

### Implemented Verification Assets

- `docs/verification_standard.md` defines high-level verification rules.
- `docs/PLAN.md` is the canonical implementation plan referenced by repo docs.
- `docs/evidence/` contains per-item evidence packs.
- `logs/verification/` contains per-item verification JSON, pending app-check
  state, and the status snapshot.
- `tools/verify_requirements.py` is the repo-owned command that writes the
  evidence index and invokes the regrade path.
- `tools/proof_verifier.py` performs the repo-wide regrade.
- `src/aetherflow/core/verification_report.py` parses plan metadata, parses
  evidence packs, evaluates plan items, and writes report payloads.
- `tools/generate_verification_report.py` currently regenerates reports through
  the same core evaluator path.
- `src/aetherflow/core/developer_app_checks.py` manages pending developer
  app-check alerts and startup snapshots.

### Current Weaknesses

- Multiple tools can emit verification outputs, which makes authority unclear.
- Heuristic or documentation-based artifacts can still look stronger than they
  are.
- Evidence packs can name tests without proving that acceptance criteria are
  exercised through the real entry point.
- Verification JSON can faithfully mirror a weak evidence pack and still not
  prove real functionality.
- Performance-sensitive claims are not safe to infer from the presence of tests
  or generated reports.
- Some verifier expectations still live as code defaults rather than explicit
  plan metadata.

## Verification Authority Model

### Canonical Sources Of Truth

- Canonical implementation plan: `docs/PLAN.md`
- Canonical repo regrade command:
  `uv run python -m tools.verify_requirements`
- Canonical evaluator:
  `src/aetherflow/core/verification_report.py`
- Canonical repo regrade driver: `tools/proof_verifier.py`
- Canonical report outputs:
  - `docs/requirements-report.md`
  - `logs/verification/<item-id>.json`

### Non-Authoritative Tools

- `tools/generate_verification_report.py` is a compatibility wrapper around the
  same evaluation model and must not be treated as a second authority.
- `tools/audit_plan_completion.py` is advisory only. It may help inspect plan
  structure or task drift, but it must never promote, verify, or prove
  functionality.
- `logs/verify-requirements-evidence.md` is a structural evidence index. It is
  useful for gap discovery and heuristic inspection, but it is not proof of
  completion.

## Proof Standard

### What Verified Means

A work item may be considered `verified` only when all of the following are
true:

- the item has explicit acceptance criteria
- each acceptance criterion has executable proof mapped to it
- the intended entry point is exercised
- relevant failure or edge paths are exercised
- declared validations pass
- the evidence pack is approved by a reviewer
- no unresolved proof gaps remain

### What Does Not Count As Proof

The following are supporting signals only and must never stand in for real
verification:

- file existence
- non-placeholder or non-thin heuristics
- report generation
- JSON generation
- evidence-pack presence
- import success
- broad smoke tests
- grep hits or path hits
- “no exception thrown”
- reviewer confidence without executable proof

### Performance-Sensitive Claims

For items that make claims about latency, FPS, throughput, responsiveness, or
runtime ceilings, `verified` must not imply “performant” without explicit
performance artifacts tied to thresholds.

## Metadata And Artifact Contracts

### Required Plan Metadata For Active AF Items

Each active `AF-*` item in `docs/PLAN.md` must explicitly define:

- `Lifecycle`
- `Feature-Class`
- `Entry-Point`
- `Acceptance Criteria`
- `Required-Proof-Types`
- `Required-Failure-Modes`
- `Evidence-Pack`
- `Validation`
- `App-Testable`
- `App-Surface` when applicable
- `Developer-Alert-Message` when applicable
- `Performance-Claim` when the item asserts measurable runtime behavior

### Evidence-Pack Requirements

Each `docs/evidence/<item-id>.md` pack must include:

- item ID and title
- acceptance criteria
- proof matrix with criterion, proof type, concrete evidence artifact, entry
  point, and failure coverage
- unresolved gaps
- reviewer decision and identity
- app-check metadata when applicable
- performance artifact references and thresholds when performance is claimed

### Verification JSON Requirements

Each `logs/verification/<item-id>.json` payload must record:

- computed status
- reviewer state
- gap list
- evidence-pack path
- validation commands
- app-check state
- acceptance-criteria coverage status
- failure-coverage status
- performance-proof status when relevant

## Remaining Closure Work

### 1. Clarify Tool Authority

- document one authoritative verification path
- explicitly downgrade wrappers and heuristic auditors to non-authoritative
  roles
- remove stale references to no-longer-canonical workflow paths

### 2. Tighten Proof Semantics

- prevent report generation and evidence-file presence from reading as proof
- require AC-to-proof mapping through the actual entry point
- require failure coverage where relevant
- require explicit performance artifacts for performance claims

### 3. Remove Hidden Defaults

- identify verifier assumptions that still live in code defaults
- move active-item expectations into `docs/PLAN.md`
- document backward-compat behavior for legacy items during migration

### 4. Convert The Current Report Into A Closure Matrix

Use `docs/requirements-report.md` as the current baseline and classify each
active non-verified item into one or more concrete closure gaps:

- metadata gap
- acceptance-criteria coverage gap
- failure-coverage gap
- validation gap
- review/sign-off gap
- performance-proof gap

### 5. Resolve App-Check Semantics

- app-check alerts are prompts for human inspection only
- app-check alerts must never count as proof
- acknowledgement behavior must be explicitly defined and documented
- startup notices and persistence must align with tests

## Current Closure Matrix Baseline

Based on the current `docs/requirements-report.md` output, the active baseline
is:

### Reviewer Sign-Off Gaps

- `AF-02-01`
- `AF-03-01`
- `AF-03-02`
- `AF-04-01`
- `AF-05-01`
- `AF-05-02`

These items currently read as `evidenced` because reviewer approval is still
pending.

### Acceptance-Criteria Coverage Gaps

- `AF-00-02b`
- `AF-00-03`
- `AF-00-04`
- `AF-00-05`
- `AF-01-01`
- `AF-01-02`
- `AF-02-02`
- `AF-04-02`

These items currently read as `evidenced` because the proof matrix does not yet
fully cover the declared acceptance criteria.

### Already Resolved Statuses

- `AF-00-01` is `retired`
- `AF-00-02a` is `verified`

This matrix must be treated as a starting point only. Before promoting any
item, the closure work must also confirm that:

- the evidence is tied to the true entry point
- the negative path is exercised where relevant
- performance claims are backed by explicit artifacts when made

## Test Plan

Add or update verification coverage for the following:

- non-authoritative tools cannot claim or promote `verified`
- active plan metadata contains explicit required-failure and performance fields
- stale evidence degrades status
- missing failure coverage blocks `verified` when relevant
- missing performance artifacts block performance-sensitive verification claims
- evidence packs must prove AC coverage, not just name a test file
- app-check alerts do not contribute to verification status

## Assumptions And Defaults

- `docs/PLAN.md` remains the canonical implementation plan
- root `PLAN.md` is the current-state gap-closure and hardening plan
- `tools/verify_requirements.py` remains the canonical repo regrade command
- `tools/generate_verification_report.py` may stay as a wrapper if clearly
  documented as non-authoritative
- `tools/audit_plan_completion.py` remains advisory only
- performance claims require explicit artifacts and thresholds
- “functional and performant” is never inferred from a sweep of files or a
  generated report

## Recommended Execution Order

1. document verification authority and non-authoritative tools
2. strengthen proof and performance semantics
3. eliminate hidden metadata defaults
4. derive the closure matrix from the current report
5. resolve app-check semantics and test alignment
