<proposed_plan>
# Evidence-Based Verification Rewrite With Developer App-Check Alerts

## Summary

Replace the current completion model, which is mostly driven by file presence,
placeholder/thin heuristics, and weak per-file test checks, with an
evidence-based verification system. A plan item must no longer become
`verified` because a script sees non-placeholder files and a validation command
returns `0`; it must become `verified` only when its claimed behavior is backed
by executable proof, mapped into an item-specific evidence pack, and approved
by a human reviewer.

Regrade all currently `verified` items under the new standard, and retire
obsolete bootstrap items that no longer protect anything meaningful, such as
one-time canonicalization work that cannot realistically regress.

Add a developer feedback loop on top of that system: whenever a newly verified
plan item declares that it is app-testable from the GUI or startup flow, the
app should generate an in-app startup notice and a persistent log entry telling
the developer that a new feature was added and should be checked in the running
application.

## Implementation Changes

### 1. Define the new verification policy

Add [docs/verification_standard.md](c:\Users\Dada\Projects\aetherflow\docs\verification_standard.md)
as the canonical policy for completion and verification.

The document should define:

- purpose and scope of the verification system
- what counts as implementation
- what counts as verification
- what does not count as proof:
  - file existence
  - line count
  - non-placeholder heuristics
  - import success
  - broad smoke tests
  - assertion-count thresholds
  - “no exceptions thrown”
  - LLM saying code “looks implemented”
- proof strength hierarchy:
  - focused integration and contract proofs
  - deterministic scenario/e2e proofs
  - unit proofs
  - static checks
  - structural heuristics
- feature-class verification rules:
  - pure logic utilities
  - service/plugin wiring
  - UI behavior
  - external boundaries such as native/proto/security
  - end-user workflows
- required proof properties:
  - one or more explicit acceptance criteria
  - one or more executable proofs per criterion
  - at least one behavioral proof
  - at least one failure or edge proof where relevant
  - intended entry point exercised
  - proof would fail if the implementation were stubbed or disconnected
- human sign-off requirement for `verified`
- developer app-check alert rule for app-testable features

### 2. Replace the status model and redefine what “verified” means

Adopt these states repo-wide:

- `drafted`: planned but not implemented
- `coded`: implementation exists but has no acceptable proof yet
- `evidenced`: acceptance criteria and proof mapping exist, but review is not
  complete
- `verified`: required proofs passed and the evidence pack was approved by a
  human reviewer
- `complete`: optional post-verification terminal state if you still want a
  merged/accepted distinction
- `retired`: obsolete item intentionally removed from readiness accounting

Rules:

- a plan item may not move directly from “files changed” to `verified`
- `verified` requires a human-approved evidence pack
- `retired` items are excluded from shipping counts and “remaining work” views
- placeholder/thin checks may block promotion but may never establish promotion

### 3. Redesign plan-item metadata in `docs/PLAN.md`

Update [docs/PLAN.md](c:\Users\Dada\Projects\aetherflow\docs\PLAN.md) so every
non-retired `AF-*` item includes explicit verification metadata, not just
target files and one validation command.

For each active item, add:

- title and current state
- acceptance criteria:
  - 1-3 concrete behavioral outcomes
- feature class:
  - `logic`
  - `service`
  - `ui`
  - `boundary`
  - `workflow`
- entry point:
  - the actual API, command, main-window path, panel action, plugin
    registration path, or startup flow used to exercise the feature
- required proof types:
  - unit, integration, contract, scenario/e2e, artifact
- required failure modes:
  - at least one meaningful bad-path or edge condition unless the item is
    truly trivial
- evidence pack path
- reviewer sign-off requirement
- validation commands
- app-testability metadata when relevant:
  - `app_testable: true|false`
  - `app_surface`: main window, panel, plugin list, button flow, startup flow,
    theme/design change, etc.
  - `developer_alert_message`: short developer-facing message for the startup
    notice

Retire obsolete items rather than preserving them as fake “verified” work.

### 4. Introduce evidence packs and machine-readable verification outputs

Use a hybrid evidence model:

- `docs/PLAN.md` stores acceptance criteria and required proof expectations
- `docs/evidence/<item-id>.md` stores the human-readable evidence pack
- `logs/verification/<item-id>.json` stores the machine-readable verification
  result

Each evidence pack must include:

- item ID and title
- current state
- acceptance criteria
- exact tests, commands, and artifacts tied to each criterion
- success-path proof
- failure or edge-path proof
- entry point exercised
- touched implementation files
- unresolved gaps if the item is only `coded` or `evidenced`
- reviewer name/identity, decision, and timestamp
- app-testability declaration when relevant

Each machine-readable verification result should include:

- item ID
- computed state
- proof summary by criterion
- required proof types
- validation command results
- missing proof categories
- sign-off presence/absence
- app-testable flag
- pending developer-alert status

### 5. Rewrite the verification workflow and promotion logic

Replace the current proof model in [.cursor/workflows/verify-requirements.ps1](c:\Users\Dada\Projects\aetherflow\.cursor\workflows\verify-requirements.ps1)
and the current thin completion behavior around [tools/validation_gate.py](c:\Users\Dada\Projects\aetherflow\tools\validation_gate.py)
with a proof-first verifier.

The new verifier should:

- parse plan-item verification metadata from `docs/PLAN.md`
- require acceptance criteria and an evidence-pack path
- reject items with vague or missing criteria
- confirm that declared tests and commands exist
- execute item-specific validations
- enforce feature-class proof requirements
- require at least one behavioral proof
- require at least one failure or edge proof where the item’s risk/surface
  warrants it
- confirm the intended entry point is actually exercised
- require human sign-off before promoting to `verified`
- generate `logs/verification/<item-id>.json`
- rebuild `docs/requirements-report.md` from evidence states rather than
  placeholder/thin heuristics

Keep structural checks as secondary hygiene only:

- missing target files can fail an item
- placeholder/thin files can fail an item
- weak tests can fail an item
- none of those may independently promote an item to `verified`

### 6. Regrade the repo under the new standard

Perform a full regrade of all currently `verified` plan items.

For each current item:

- if it has meaningful acceptance criteria, executable proof, and
  reviewer-approved evidence, keep or restore `verified`
- if implementation exists but proof is weak or unmapped, downgrade to `coded`
  or `evidenced`
- if the item is obsolete plan debt, mark it `retired`

Update [docs/requirements-report.md](c:\Users\Dada\Projects\aetherflow\docs\requirements-report.md)
so it reports the new states:

- `retired`
- `drafted`
- `coded`
- `evidenced`
- `verified`
- `complete` if retained

Per-item reporting should also include:

- missing proof types
- missing failure coverage
- missing sign-off
- missing or stale evidence pack
- stale validation output
- whether the item is app-testable
- whether a developer alert is pending, acknowledged, or not applicable

### 7. Add developer startup alerts for newly verified app-testable features

Use the existing shell notice mechanism in [src/aetherflow/ui/shell.py](c:\Users\Dada\Projects\aetherflow\src\aetherflow\ui\shell.py)
as the in-app delivery point.

Behavior:

- when an item transitions to `verified` and its metadata says
  `app_testable: true`, create a pending developer app-check alert
- store pending alerts in a persistent machine-readable file such as
  `logs/verification/pending_app_checks.json`
- on app startup, load pending alerts and inject them into the shell notice
  list
- each notice should include:
  - item ID
  - short message such as “New feature added, check for functionality”
  - affected app surface
  - optional evidence-pack reference
- also record the alert in a persistent developer-facing log or diagnostics
  artifact
- allow acknowledgement from inside the app so the alert stops reappearing once
  reviewed

Trigger rule:

- trigger only when the evidence pack explicitly declares the feature
  app-testable
- do not trigger merely because UI/plugin files changed
- examples that should qualify:
  - new input plugin visible in the app
  - new output plugin route or panel
  - new main-window flow or button
  - theme/design changes the developer can inspect by launching the app
  - new startup or plugin-registration behavior visible from the shell

Default migration behavior:

- do not backfill alerts for all previously implemented items during regrade
- only create alerts for features whose verification transition happens after
  the new system is in place, unless a backlog seeding step is explicitly added
  later

## Important Interfaces And Artifacts

New or changed public repo interfaces:

- [docs/verification_standard.md](c:\Users\Dada\Projects\aetherflow\docs\verification_standard.md)
- expanded plan-item verification metadata in [docs/PLAN.md](c:\Users\Dada\Projects\aetherflow\docs\PLAN.md)
- human-readable evidence packs under `docs/evidence/<item-id>.md`
- machine-readable verifier outputs under `logs/verification/<item-id>.json`
- pending developer-alert queue under
  `logs/verification/pending_app_checks.json`
- updated state/report semantics in [docs/requirements-report.md](c:\Users\Dada\Projects\aetherflow\docs\requirements-report.md)

The verifier should treat these artifacts as canonical inputs/outputs rather
than inferring completion from file structure alone.

## Test Plan

Add verification-system tests for:

- item without acceptance criteria is rejected
- item without evidence pack is rejected
- item with only structural checks and no behavioral proof is rejected
- item missing required failure or edge proof is rejected when relevant
- item missing reviewer sign-off cannot become `verified`
- retired items are excluded from readiness counts
- requirements report is generated from evidence states rather than placeholder
  heuristics
- a previously “verified” item is downgraded during regrade when evidence is
  insufficient
- feature-class rules are enforced:
  - logic item
  - service/plugin item
  - UI item
  - boundary item
  - workflow item

Add developer-alert tests for:

- newly verified `app_testable=true` item creates a pending alert
- non-app-testable item does not create an alert
- startup loads pending alerts into shell notices
- alert message includes item ID and app surface
- alert is recorded in persistent log output
- acknowledgement clears the pending alert
- duplicate startups do not duplicate pending alerts
- regraded legacy items do not automatically spam alerts unless explicitly
  configured

Add one end-to-end fixture proving the full chain:

- plan item metadata
- evidence pack
- validation execution
- human sign-off
- verified promotion
- pending alert creation
- app startup notice
- acknowledgement
- alert persistence/logging

## Assumptions And Defaults

- human sign-off approves the evidence pack, not just the diff
- evidence storage is hybrid:
  - policy in `docs/verification_standard.md`
  - requirements in `docs/PLAN.md`
  - evidence packs in `docs/evidence/`
  - machine outputs in `logs/verification/`
- placeholder/thin checks remain as secondary hygiene gates only
- obsolete bootstrap items are marked `retired`
- developer alerts are delivered in-app plus persistent log by default
- no external notification channel is added in this rewrite
- the first implementation slice after planning should be:
  1. policy document and state model
  2. plan metadata and evidence-pack schema
  3. verifier rewrite
  4. repo-wide regrade
  5. developer startup-alert flow
</proposed_plan>
