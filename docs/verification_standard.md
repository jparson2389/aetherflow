# Verification Standard

## Purpose

This document defines what counts as implementation and what counts as
verification in Aetherflow.

The goal is to prevent work items from being marked complete because files
exist, tests are tiny, or one generic command happens to pass. A work item is
verified only when its claimed behavior is backed by executable proof, tied to
explicit acceptance criteria, and approved by a human reviewer.

## Definitions

- _Implementation_: code or documents exist for the claimed work item.
- _Behavioral proof_: executable evidence showing an observable effect through
  the intended entry point.
- _Structural checks_: file existence, placeholder scans, lint, or import
  success. These can block progress but cannot prove completion.
- _Evidence pack_: item-specific proof record that ties acceptance criteria to
  commands, tests, and reviewer sign-off.

## Verification States

- `drafted`: required targets are missing.
- `coded`: implementation exists but no acceptable evidence pack exists yet.
- `evidenced`: an evidence pack exists, but proof or sign-off is incomplete.
- `verified`: required proofs pass and the evidence pack is approved.
- `complete`: optional post-verification terminal state.
- `retired`: obsolete item intentionally removed from readiness accounting.

## Evidence Requirements

Every non-retired item must define:

- 1-3 explicit acceptance criteria
- at least one executable proof per criterion
- at least one behavioral proof
- at least one failure or edge proof when the item has meaningful risk
- the intended entry point that exercises the behavior
- a reviewer sign-off before promotion to `verified`

## What Does Not Count As Proof

These are supporting signals only:

- file existence
- line count
- placeholder or thin-file heuristics
- import success
- generic smoke tests
- assertion-count thresholds
- "no exceptions thrown"
- model or LLM judgment that code "looks implemented"

## Proof Strength Hierarchy

Strongest to weakest:

1. Focused integration or contract proof tied to acceptance criteria
2. Deterministic scenario or end-to-end proof
3. Focused unit proof of critical logic
4. Static checks
5. Structural heuristics

## Feature-Class Rules

- `logic`: focused unit proof plus meaningful edge handling
- `service`: integration proof through the service boundary
- `ui`: deterministic UI or shell-level proof through the intended surface
- `boundary`: contract proof and negative-path validation
- `workflow`: scenario or contract proof showing the feature is reachable and
  bounded correctly

## Failure Conditions

An item may not be promoted to `verified` when:

- acceptance criteria are missing or vague
- no behavioral proof exists
- required proof types are missing
- the intended entry point is not exercised
- failure or edge coverage is missing where relevant
- reviewer sign-off is not approved

## Developer App-Check Alerts

If a newly verified item is marked app-testable from the GUI or startup flow,
the verification pipeline must create a developer alert when it detects a
transition from a non-verified status to `verified`.

The alert rules are:

- emit an in-app startup notice
- persist the alert in a machine-readable log
- do not backfill alerts for already-verified legacy work on initial baseline
- clear the alert once the developer acknowledges it

**Clean-checkout and initial-baseline behaviour:** Transition detection requires
a prior `logs/verification/status_snapshot.json` to compare against. When no
snapshot exists (clean checkout, first run), the pipeline writes the current
statuses as the baseline and emits no alerts — the "do not backfill" rule
applies to all items seen for the first time. Alert detection therefore requires
at least two consecutive local runs of `uv run python -m tools.verify_requirements`
with the item transitioning to `verified` in between. This is by design:
`status_snapshot.json` is Tier 2 generated runtime output (see
`docs/governance/artifact-storage-policy.md`) and is not git-tracked.

## Acknowledging an Alert

An alert is triggered when a plan item transitions to `verified` and carries
`App-Testable: true`. The developer must manually confirm the surface behaviour
and then acknowledge the alert to clear it.

**What triggers an alert:** a plan item moves to `verified` status and its
evidence pack declares `App-Testable: true`. The verification pipeline writes
the alert to `logs/verification/pending_app_checks.json`.

**List pending alerts:**

```text
uv run python -m tools.verify_requirements
```

Pending alerts are printed as a startup notice when the tool runs.

**Acknowledge an alert:**

```text
uv run python -m tools.verify_requirements --acknowledge <item-id>
```

For example:

```text
uv run python -m tools.verify_requirements --acknowledge AF-01-02
```

**Effect:** the alert is removed from `logs/verification/pending_app_checks.json`.
The item remains `verified` — acknowledgement only clears the pending notice.
