# Verification Standard

## Purpose

This document defines what counts as implementation and what counts as
verification in Aetherflow.

The goal is to prevent work items from being marked complete because files
exist, tests are tiny, or one generic command happens to pass. A work item is
verified only when its claimed behavior is backed by executable proof, tied to
explicit acceptance criteria, and approved by a human reviewer.

## Definitions

- *Implementation*: code or documents exist for the claimed work item.
- *Behavioral proof*: executable evidence showing an observable effect through
  the intended entry point.
- *Structural checks*: file existence, placeholder scans, lint, or import
  success. These can block progress but cannot prove completion.
- *Evidence pack*: item-specific proof record that ties acceptance criteria to
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
the verification pipeline must create a developer alert.

The alert rules are:

- emit an in-app startup notice
- persist the alert in a machine-readable log
- do not backfill alerts for already-verified legacy work on initial baseline
- clear the alert once the developer acknowledges it
