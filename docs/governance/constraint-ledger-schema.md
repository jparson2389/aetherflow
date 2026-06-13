# Constraint Ledger Schema

## Purpose

Canonical machine-readable schema for tracked governance items in the Aetherflow
execution governance system. Defines the shared item model, lifecycle states,
source traceability, evidence links, supersession fields, and ownership metadata
required by issues #13–#27.

**Applicable item types:** `constraint` · `plan-item` · `phase-exit` · `dossier`

---

## Schema Version

```yaml
schema_version: "1.0"
```

Increment the minor version for additive changes; increment the major version for
breaking changes to required fields or state machine transitions.

---

## Base Item Fields (all types)

Every governance item, regardless of type, carries the following fields.

```yaml
# ── Identity ──────────────────────────────────────────────────────────────────
schema_version: "1.0"          # string — must match the file's declared version
id: "CL-001"                   # string — globally unique; format is type-specific:
                               #   CL-<NNN>  constraint  (3-digit zero-padded, e.g. CL-001)
                               #   PI-<NNN>  plan-item   (3-digit zero-padded, e.g. PI-042)
                               #   PE-<NN>   phase-exit  (2-digit zero-padded, e.g. PE-00)
                               #   DO-<slug> dossier     (plugin slug, e.g. DO-my-plugin)
type: constraint               # enum: constraint | plan-item | phase-exit | dossier
title: "Short claim title"     # string — one sentence, present tense
parent: null                   # id | null — parent item id, null for root items

# ── Source traceability ────────────────────────────────────────────────────────
source:
  file: "docs/PRD.md"          # string — repo-relative path
  ref: "§2 Guidelines"         # string — section, line, or anchor
  trust: primary               # enum: primary | secondary
  secondary_reason: null       # string | null — required when trust is secondary;
                               #   explains why no primary source was available
  claim: >                     # string — normalized statement of the constraint or
                               #   capability, in plain English, as extracted from source

# ── Classification ─────────────────────────────────────────────────────────────
classification:                # list<enum> — one or more of:
  - architectural              #   architectural | process | testing |
                               #   dependency | security | verification
                               #   topical category only — the subject area of the
                               #   claim, NOT how it is proven (see proof_claim_type)

# ── Proof claim type ─────────────────────────────────────────────────────────────
proof_claim_type: structural   # enum: measurable | observable | structural
                               #   classifies the claim by how acceptable proof is
                               #   determined up front (PRD user story #26):
                               #     measurable  → proven by a quantified metric
                               #     observable  → proven by a produced runtime artifact
                               #     structural  → proven by repo structure/configuration
                               #   distinct from topical `classification` above:
                               #   classification = subject area; proof_claim_type = proof model

# ── Lifecycle state ────────────────────────────────────────────────────────────
state: draft                   # enum — see State Machine section below

# ── State history (append-only) ────────────────────────────────────────────────
state_history:
  - state: draft               # enum — the state entered at this record
    timestamp: "2026-05-23T00:00:00Z"   # ISO 8601 UTC
    actor: "agent:claude-code"          # string — agent:<name> or human:<username>
    rationale: "Initial extraction from PRD"  # string — why this transition occurred
    evidence_ref: null         # id | null — links to an evidence record if applicable

# ── Evidence records (append-only) ─────────────────────────────────────────────
evidence: []
# Each record:
#   id:            string — EV-<item-id>-<n>, e.g. EV-CL-001-1
#   type:          enum — runtime-artifact | measurement | diagnostic |
#                         smoke-review | manual-review
#   description:   string — what this evidence proves
#   artifact_ref:  string — repo-relative path or URL to the produced artifact
#   timestamp:     ISO 8601 UTC
#   produced_by:   string — agent:<name> or human:<username>
#   superseded:    bool — true if a later record replaces this one
#   superseded_reason: string | null

# ── Acceptance ──────────────────────────────────────────────────────────────────
acceptance:
  accepted: false              # bool
  accepted_by: null            # string | null — must be human:<username>; agents cannot accept
  accepted_at: null            # ISO 8601 UTC | null
  review_packet_ref: null      # string | null — path to the review packet artifact
  conditions: null             # string | null — any stated conditions on this acceptance

# ── Supersession ────────────────────────────────────────────────────────────────
supersession:
  superseded_by: null          # id | null — the item that replaces this one
  supersedes: null             # id | null — the item this one replaces
  reason: null                 # string | null — why the supersession occurred

# ── Ownership ───────────────────────────────────────────────────────────────────
ownership:
  owner: "human:jparson2389"   # string — human:<username> or team:<name>
  authority_tier: human        # enum: human | agent
                               #   human  → agents may advance to evidenced;
                               #            only a human may advance to accepted
                               #   agent  → agents may self-advance to evidenced;
                               #            humans still required for accepted
  update_trigger: ""           # string — condition that requires re-review of this item

# ── Invalidation ────────────────────────────────────────────────────────────────
invalidation:
  status: none                 # enum: none | soft | hard
  triggers: []
  # Each trigger:
  #   condition: string — what change would activate this trigger
  #   type:      enum — soft | hard
  #   downgrade_to: enum — target state on activation (soft: evidenced; hard: draft or researched)
  active_trigger: null         # string | null — description of the currently active trigger
  downgrade_target_state: null # enum | null — state to downgrade to when invalidation fires
```

---

## Constraint Variant (type: constraint)

Adds enforcement-specific fields to the base schema. All base fields are still
required.

```yaml
# ── Constraint-specific ──────────────────────────────────────────────────────
constraint:
  enforcement_mechanism: null  # string | null — how the repo enforces this claim;
                               #   null means undetermined
  enforcement_status: undetermined
                               # enum: enforced | weak | ambiguous | false | undetermined
                               #   enforced     → repo demonstrably enforces the claim
                               #   weak         → partial or soft enforcement exists
                               #   ambiguous    → conflicting signals; needs manual review
                               #   false        → claim is stated but repo does not enforce it
                               #   undetermined → not yet audited
  rejection_proof_ref: null    # string | null — path to evidence that the repo rejects
                               #   violations; required for enforced status
  audit_notes: ""              # string — free-form notes from the enforcement audit
```

---

## Plan-Item Variant (type: plan-item)

Extends base schema for leaf and parent execution plan items.

```yaml
# ── Plan-item-specific ────────────────────────────────────────────────────────
plan_item:
  item_kind: leaf              # enum: leaf | parent
                               #   leaf   → implementable, evidenceable, acceptable;
                               #            may enter scaffolded and implemented states
                               #   parent → grouping only; completion derived from accepted leaves;
                               #            must NOT enter scaffolded or implemented states
  dossier_ref: null            # id | null — the DO- dossier that defines the contract
  dossier_sections: []         # list<string> — specific sections within the dossier;
                               #   REQUIRED (non-empty) when dossier_ref is set: a
                               #   plugin-backed plan item must anchor to the dossier
                               #   sections that define its contract (PRD: "every plan
                               #   item must point at the dossier sections"). May remain
                               #   empty only when dossier_ref is null (non-plugin items)
  primary_evidence_req: null   # string | null — the single primary evidence obligation;
                               #   REQUIRED (non-null) when item_kind: leaf — validators must
                               #   reject acceptance of a leaf item without a primary evidence
                               #   requirement (PRD user story #12)
  parent_capability: null      # id | null — the PI- capability group this leaf rolls up to;
                               #   REQUIRED (non-null) when item_kind: leaf — validators must
                               #   reject acceptance of a leaf item without a parent capability
                               #   (PRD user story #12); distinct from the base `parent` field:
                               #   `parent` is the immediate hierarchy parent (any type, e.g.
                               #   PE-); this field is always a PI- node for rollup reporting
  responsible_files: []        # list<string> — files this item concretely modifies;
                               #   not a "may touch" list
```

**Leaf-item required fields:** When `item_kind: leaf`, the following fields are mandatory
(non-null). Validators must reject acceptance of any leaf item that omits them:

- `parent_capability` — every leaf must roll up to exactly one PI- capability group
- `primary_evidence_req` — every leaf must declare exactly one primary evidence obligation

Parent plan-items (`item_kind: parent`) leave both fields null; their completion is derived
solely from accepted leaf descendants.

---

## Phase-Exit Variant (type: phase-exit)

Extends base schema for tracked phase completion items.

```yaml
# ── Phase-exit-specific ──────────────────────────────────────────────────────
phase_exit:
  phase: 0                     # int — the phase number this item gates
  prerequisite_item_ids: []    # list<id> — all items that must be accepted
                               #   before this phase-exit can reach evidenced
```

---

## Dossier Variant (type: dossier)

Extends base schema for plugin research dossiers.

```yaml
# ── Dossier-specific ─────────────────────────────────────────────────────────
dossier:
  plugin: ""                   # string — canonical plugin name
  contracts: []
  # Each contract:
  #   capability: string
  #   required_apis: list<string>
  #   os_facilities: list<string>
  #   forbidden_substitutes: list<string>
  anti_patterns: []
  # Each anti-pattern:
  #   pattern: string
  #   detection: string
  #   real_implementation: string
  evidence_map: []
  # Each entry:
  #   capability: string
  #   proof_class: enum — runtime-artifact | measurement | diagnostic | smoke-review | manual-review
  #   invalidation_criteria: string
  # For dossiers: the base `source` field holds the canonical anchor document
  # (the single most authoritative reference). `source_trust` lists all aggregated
  # sources including the anchor. Populate both fields — base `source` is the anchor,
  # `source_trust` is the full set.
  source_trust: []
  # Each entry:
  #   source: string
  #   trust: primary | secondary
  #   notes: string
```

---

## State Machine

Items advance through lifecycle states. The table below defines who may trigger
each transition and what evidence is required.

```text
draft
  │  actor: agent or human
  │  requires: source fields populated, claim normalized
  ▼
researched
  │  actor: agent or human
  │  requires: enforcement_mechanism assessed (constraints only),
  │            source trust recorded
  ▼
contract-defined            ← constraints skip this state
  │  actor: agent or human
  │  requires (plan-items): dossier_ref set, non-empty dossier_sections,
  │            and responsible_files listed. Contract tests must reject a
  │            plugin-backed plan-item that omits dossier section anchors
  │            before it can reach ready.
  ▼
ready
  │  actor: agent or human
  │  requires: all prerequisite items accepted or not applicable
  ▼
scaffolded                  ← plan-items (item_kind: leaf) only; constraints and parent plan-items skip
  │  actor: agent
  │  requires: structural file skeletons present
  ▼
implemented                 ← plan-items (item_kind: leaf) only; constraints and parent plan-items skip
  │  actor: agent
  │  requires: implementation complete per contract
  ▼
evidenced
  │  actor: agent (may reach evidenced; may NOT self-advance to accepted)
  │  requires: at least one non-superseded evidence record of allowed type
  ▼
accepted                    ← HUMAN ONLY; agents must not self-advance here
  │  actor: human only
  │  requires: acceptance.accepted_by is human:<username>,
  │            review_packet_ref populated,
  │            all prerequisite items accepted
```

**Parent plan-item lifecycle note:** Items with `plan_item.item_kind: parent` are
grouping-only. They may not enter `scaffolded` or `implemented` states directly.
A parent item reaches `evidenced` only when all of its accepted leaf descendants
have been accepted; it may not self-advance through implementation transitions.
Validators must reject any state write of `scaffolded` or `implemented` on a
parent plan-item.

Retirement may occur from any state:

```text
any state → retired
  actor: human only
  requires: state_history entry with rationale
```

Invalidation downgrades (any accepted or evidenced item):

```text
accepted/evidenced → downgrade_target_state
  soft invalidation: → evidenced  (re-evidence required; acceptance revoked)
  hard invalidation: → draft or researched  (full re-audit required)
```

---

## Evidence Types

Only the following evidence types count toward state advancement. Tests do not
count as closure evidence (tests are TDD support only).

<!-- prettier-ignore-start -->
| Type | Description | Allowed for accepted |
|------|-------------|---------------------|
| `runtime-artifact` | Produced artifact from a running system (log, snapshot, trace) | Yes |
| `measurement` | Quantified metric output (latency, FPS, throughput) | Yes |
| `diagnostic` | Tool-produced diagnostic output (lint clean, schema validation pass) | Yes |
| `smoke-review` | Structured human smoke review with defined checklist | Yes |
| `manual-review` | Bounded human review justified by dossier contract | Yes |
<!-- prettier-ignore-end -->

`smoke-review` and `manual-review` may only be used when the dossier or item
record explicitly authorizes them. They may not substitute for automatable proof.

---

## Enforcement Status (constraints only)

<!-- prettier-ignore-start -->
| Value | Meaning |
|-------|---------|
| `enforced` | Repo demonstrably enforces the claim; rejection proof exists |
| `weak` | Partial or soft enforcement; claim is stated but not fully guarded |
| `ambiguous` | Conflicting signals; requires explicit human resolution |
| `false` | Claim is in documentation but repo does not enforce it |
| `undetermined` | Audit not yet performed |
<!-- prettier-ignore-end -->

---

## Authority Rules

- `authority_tier: human` → only a human may advance from `evidenced` to `accepted`;
  agents may advance to `evidenced`.
- `authority_tier: agent` → agents may advance items through `implemented` and
  produce `evidenced` records, but **only humans may set `acceptance.accepted: true`**.
- Agents must never set `acceptance.accepted: true`.
- Evidence and state-history records are **append-only**. Supersede records
  instead of modifying or deleting them.

---

## Supersession Rules

- When a constraint is superseded, `superseded_by` must reference the replacing
  item's id before the original is retired.
- Superseded items must not be deleted; they must transition to `retired` with
  `supersession.reason` populated.
- A superseding item must set `supersedes` to the original item's id.

---

## Invalidation Triggers

Triggers are declared per item and fire when the described condition is observed.

```yaml
invalidation:
  triggers:
    - condition: "docs/PRD.md §2 section is materially rewritten"
      type: soft
      downgrade_to: evidenced
    - condition: "enforcement mechanism file is deleted or renamed"
      type: hard
      downgrade_to: researched
```

Global material-change heuristics (apply unless overridden per item):
- Soft: source file section content changes by >20 lines or changes claim meaning.
- Hard: enforcement mechanism file deleted, frozen contract modified, or phase
  prerequisite item invalidated.

---

## Full Example: Constraint Item

```yaml
schema_version: "1.0"
id: "CL-001"
type: constraint
title: "Platform scope is Windows-only for v1"
parent: null

source:
  file: "docs/PRD.md"
  ref: "§2 Guidelines"
  trust: primary
  secondary_reason: null
  claim: >
    The v1 release targets Windows exclusively; no other OS is in scope.

classification:
  - architectural

proof_claim_type: structural

state: researched

state_history:
  - state: draft
    timestamp: "2026-04-24T00:00:00Z"
    actor: "agent:claude-code"
    rationale: "Extracted from PRD §2 during constraint inventory pass (issue #14)"
    evidence_ref: null
  - state: researched
    timestamp: "2026-04-24T00:00:00Z"
    actor: "agent:claude-code"
    rationale: "Source trust confirmed primary; enforcement status assessed"
    evidence_ref: null

evidence: []

acceptance:
  accepted: false
  accepted_by: null
  accepted_at: null
  review_packet_ref: null
  conditions: null

supersession:
  superseded_by: null
  supersedes: null
  reason: null

ownership:
  owner: "human:jparson2389"
  authority_tier: human
  update_trigger: "PRD §2 platform scope section is modified"

invalidation:
  status: none
  triggers:
    - condition: "PRD §2 Guidelines adds non-Windows platform"
      type: hard
      downgrade_to: draft
  active_trigger: null
  downgrade_target_state: null

constraint:
  enforcement_mechanism: null
  enforcement_status: undetermined
  rejection_proof_ref: null
  audit_notes: ""
```

---

## File Location Convention

<!-- prettier-ignore-start -->
| Item type | Storage path |
|-----------|-------------|
| `constraint` | `docs/governance/ledger/constraints/CL-<NNN>.yaml` |
| `plan-item` | `docs/governance/ledger/plan-items/PI-<NNN>.yaml` |
| `phase-exit` | `docs/governance/ledger/phase-exits/PE-<NN>.yaml` |
| `dossier` | `docs/governance/dossiers/DO-<plugin-slug>.yaml` |
<!-- prettier-ignore-end -->

The constraint inventory table in `docs/governance/constraint-inventory.md`
(produced by issue #14) remains the prose-readable index. Individual YAML ledger
files are the machine-readable authority. On conflict, the YAML ledger file wins.

---

## Changelog

<!-- prettier-ignore-start -->
| Version | Date | Author | Summary |
|---------|------|--------|---------|
| 1.0 | 2026-05-23 | agent:claude-code | Initial schema — issue #15 |
<!-- prettier-ignore-end -->
