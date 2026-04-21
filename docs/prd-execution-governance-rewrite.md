# PRD: Execution Governance Rewrite

## Problem Statement

Aetherflow's current execution governance is not trustworthy enough to support
AI-assisted delivery. The existing plan structure is too shallow, phase exit is
too easy to satisfy cosmetically, and foundational constraints are often stated
in documentation without direct proof that the repository actually enforces
them.

In practice, broad work items with long target-file lists allow agents to
optimize for file existence or superficial code presence instead of real runtime
capability. Flat phase exit command blocks treat test execution as a proxy for
truth, even when the real obligation is stronger: observable runtime behavior,
measured performance, enforced constraints, or explicit human review. This
creates a recurring failure mode where scaffolding, stubs, synthetic evidence,
or weakly connected code paths are marked complete despite not satisfying the
intended system behavior.

The repository also lacks a single authoritative model for answering critical
questions such as:

- Which foundational constraints are actually enforced today?
- Which claims come from the PRD versus implementation research versus the plan?
- What evidence is sufficient for a given type of claim?
- When is manual review acceptable?
- What invalidates prior evidence or acceptance?
- Who is allowed to accept work as authoritative?

Without a stronger governance system, the repo will continue to drift toward
documented intent instead of enforced truth.

## Solution

Replace the current execution governance model with a layered, traceable, and
phase-blocking system built around four canonical artifact types:

- a foundational constraint ledger that audits what the repo truly enforces,
- an evidence catalog and review-packet model that defines what proof counts,
- plugin dossiers that translate research into implementation contracts and
  anti-pattern detection,
- a parent/leaf execution plan and tracking ledger that blocks progress by
  dependency state, evidence state, invalidation status, and explicit human
  acceptance.

The new system separates product truth from implementation truth and execution
truth:

- The PRD defines product outcomes, obligations, and performance promises.
- Plugin dossiers define domain-specific technical reality, required APIs,
  forbidden fake substitutes, required evidence, and invalidation rules.
- The PLAN decomposes those contracts into small atomic leaf items that can be
  implemented, evidenced, and accepted.

Phase completion is no longer a flat command block. A phase becomes a tracked
item whose acceptance depends on accepted prerequisite constraints, accepted
parent capabilities, accepted leaf items, and satisfied phase-level evidence
obligations. Tests remain important for TDD and regression protection, but they
do not count as closure evidence by themselves.

## User Stories

1. As the repository owner, I want foundational constraints audited against the
   actual repo, so that documentation claims are not mistaken for enforcement.
2. As the repository owner, I want every foundational claim classified as
   enforced, weak, ambiguous, or false, so that Phase 0 becomes a trustworthy
   baseline.
3. As the repository owner, I want a machine-readable constraint ledger, so
   that later planning can depend on verified truth instead of prose.
4. As the repository owner, I want every tracked item to have an explicit
   state, so that `done` is no longer overloaded.
5. As the repository owner, I want agents to stop at `evidenced`, so that only
   humans can ratify accepted repo truth.
6. As the repository owner, I want each state transition to require a concrete
   record, so that progress cannot be asserted without an audit trail.
7. As the repository owner, I want evidence and acceptance records to be
   append-only, so that failed attempts and superseded proofs remain visible.
8. As the repository owner, I want invalidation rules, so that previously
   accepted work is downgraded when requirements or code materially change.
9. As the repository owner, I want invalidation to distinguish soft from hard
   cases, so that the system stays strict without becoming unusably brittle.
10. As the repository owner, I want phase exit modeled as a tracked item, so
    that a phase cannot close through informal interpretation.
11. As the repository owner, I want parent items to express grouping only, so
    that only leaf items can be implemented, evidenced, and accepted.
12. As the repository owner, I want every leaf item to map to exactly one
    parent capability and one primary evidence requirement, so that leaf scope
    remains unambiguous.
13. As the repository owner, I want every parent capability to remain
    incomplete until all of its leaf items are accepted, so that there is no
    partial credit from scaffolding.
14. As the repository owner, I want every phase to depend on accepted parent
    capabilities and accepted prerequisites, so that downstream work cannot
    outrun unstable foundations.
15. As the repository owner, I want every work item to declare concrete
    responsibilities, so that `Target File` no longer means “may touch this
    file.”
16. As the repository owner, I want large items decomposed into atomic leaves,
    so that an agent cannot satisfy a theme by creating thin stubs across many
    files.
17. As the repository owner, I want hard numeric limits on leaf scope, so that
    the plan stays maintainable and reviewable.
18. As the repository owner, I want plugin-specific research to be mandatory
    before implementation, so that technical ambiguity does not leak into the
    plan.
19. As the repository owner, I want each plugin to have a canonical dossier, so
    that implementation starts from auditable domain truth rather than memory or
    scattered notes.
20. As the repository owner, I want each dossier to define required runtime
    behavior, so that an agent cannot plausibly interpret “capture” or
    “translation” in a weak way.
21. As the repository owner, I want each dossier to name required APIs and OS
    facilities, so that real implementations are anchored to concrete technical
    dependencies.
22. As the repository owner, I want each dossier to list fake-implementation
    anti-patterns, so that known shortcuts are explicitly disqualifying.
23. As the repository owner, I want every anti-pattern to include a detection
    method, so that blockers are concrete rather than subjective.
24. As the repository owner, I want every anti-pattern to explain what real
    implementation looks like instead, so that the rejection is actionable.
25. As the repository owner, I want each dossier to include an evidence map, so
    that each capability has a fixed proof model and invalidation criteria.
26. As the repository owner, I want claim types classified as measurable,
    observable, or structural, so that acceptable proof is determined up front.
27. As the repository owner, I want only a small set of canonical proof
    classes, so that the governance system remains maintainable.
28. As the repository owner, I want manual review to be structured and rare, so
    that it cannot become the new loophole.
29. As the repository owner, I want manual review allowed only when explicitly
    justified by the dossier contract, so that automatable behavior still
    requires stronger proof.
30. As the repository owner, I want tests to remain part of TDD, so that
    implementation quality improves even though tests are no longer treated as
    closure evidence.
31. As the repository owner, I want closure evidence to be runtime-produced
    artifacts, measured outputs, diagnostics, and formal review records, so
    that phases close on observed truth.
32. As the repository owner, I want every dossier claim to prefer primary
    sources, so that implementation truth is not derived from low-trust
    summaries.
33. As the repository owner, I want secondary sources used only when documented
    gaps remain, so that research stays bounded and defensible.
34. As the repository owner, I want the review packet for acceptance to be
    small and fixed, so that human approval remains practical.
35. As the repository owner, I want every item to be reviewable in isolation,
    so that acceptance does not require rereading broad surrounding prose.
36. As the repository owner, I want all governing docs audited together, so
    that conflicting claims are surfaced as explicit findings.
37. As the repository owner, I want ambiguous or conflicting foundational claims
    resolved before dependent work becomes ready, so that downstream execution
    inherits stable truth.
38. As the repository owner, I want dependency blocking to understand both code
    and truth dependencies, so that research, enforcement, and implementation
    all participate in readiness.
39. As the repository owner, I want predecessor state requirements to be
    explicit, so that dependencies cannot be interpreted loosely.
40. As the repository owner, I want canonical governance artifacts to be
    review-controlled, so that agents can assist but not become the source of
    authority.

## Implementation Decisions

- Build the governance rewrite as a documentation-and-tracking system first,
  before any repo implementation rewrite work begins.
- Preserve the current PRD and PLAN as historical inputs during transition, then
  supersede them explicitly once replacement artifacts are authoritative.
- Create a foundational audit pass that extracts constraints from all governing
  sources and inspects the repository directly for enforcement proof.
- Introduce a canonical constraint ledger with one tracked record per
  foundational claim.
- Distinguish between documentation claims and enforced repo truth in all
  foundational analysis.
- Require an explicit enforcement mechanism field for foundational claims and
  for later work items where enforcement matters.
- Treat missing rejection proof as a distinct weakness for enforceable claims.
- Require violation experiments or equivalent rejection evidence for Phase 0
  enforceable constraints.
- Create a canonical evidence catalog with a small, bounded vocabulary of proof
  classes.
- Treat tests as support for TDD and regression only; they do not count as
  closure evidence by themselves.
- Allow closure evidence only through runtime artifacts, measurements,
  diagnostics, structured smoke review, and tightly controlled manual review.
- Introduce a formal item lifecycle with states including draft, researched,
  contract-defined, ready, scaffolded, implemented, evidenced, accepted, and
  retired.
- Reserve `accepted` for explicit human sign-off on phase-blocking items and
  foundational truth.
- Require all item state transitions to be justified by linked evidence or
  review records.
- Store item status, dependency state, evidence links, invalidation status, and
  acceptance history in a canonical tracking ledger.
- Model phases as tracked items rather than prose-only summaries.
- Use a parent/leaf plan structure in which parents express grouping only and
  only leaf items are implementable or acceptable.
- Enforce hard decomposition limits so leaf items remain atomic and reviewable.
- Require every leaf item to map to exactly one parent capability and one
  primary evidence requirement.
- Make parent completion and phase completion purely derived from accepted
  dependencies.
- Introduce plugin dossiers as a hard prerequisite for implementation work.
- Keep one canonical dossier per plugin, stored in a versioned repo path.
- Require each dossier to include implementation contracts, evidence maps,
  anti-patterns, detection methods, source-trust data, and invalidation rules.
- Require every plan item to point at the dossier sections that define its
  implementation contract.
- Separate product truth, research truth, and execution truth into PRD, dossier,
  and PLAN layers respectively.
- Prefer primary sources for dossier claims and record why any secondary source
  was needed.
- Use conservative invalidation by default, with explicit soft and hard
  invalidation triggers.
- Define material change heuristics globally and refine them per plugin or
  domain where needed.
- Keep governance maintainable through bounded schema size, bounded review
  packet size, a small evidence vocabulary, and numeric limits on decomposition.
- Treat human authority as the maintenance owner for canonical governance
  artifacts, with agents limited to proposal and evidence generation.

## Testing Decisions

- Good tests verify externally observable behavior and contract outcomes rather
  than implementation trivia, file existence, or constant values.
- TDD remains mandatory for agents implementing work, but passing tests do not
  themselves satisfy closure evidence obligations.
- Foundational governance work should be tested through contract-oriented checks
  that validate schemas, dependency rules, invalidation rules, and rejection
  behavior for broken constraints.
- The most valuable tests for the governance rewrite are negative tests that
  prove weak evidence, ambiguous dependencies, missing dossier prerequisites, or
  stale acceptance states are rejected correctly.
- The modules or subsystems that should receive the strongest direct test focus
  are the constraint-ledger pipeline, evidence catalog enforcement, tracking
  ledger lifecycle rules, invalidation engine, and phase-exit dependency
  evaluation.
- Prior art in the repo already exists for verification and evidence-oriented
  thinking, especially the verification-reporting and requirements-verification
  areas, but the new governance system must harden those ideas into authoritative
  lifecycle and acceptance behavior.
- Manual review forms should not be “tested” by asserting prose fields alone;
  tests should validate whether the system accepts or rejects a review packet
  based on required structure and allowed usage conditions.
- Plugin dossier consumption should be tested at the contract level: an item
  without the required dossier sections should fail readiness or acceptance.

## Out of Scope

- Rewriting the entire implementation plan in this PRD itself.
- Performing the foundational audit in this PRD itself.
- Writing plugin dossiers for every plugin in this PRD itself.
- Refactoring application runtime code as part of the governance rewrite
  definition.
- Changing frozen runtime contracts solely because the governance system is
  changing.
- Automating all manual review away; some observable-runtime behaviors may still
  require bounded human verification.
- Allowing agents to self-accept canonical truth or phase completion.
- Creating an unbounded research corpus or market-study style documentation for
  plugins.

## Further Notes

- The rewrite should proceed from Phase 0 onward, not by piloting only the most
  obviously measurable later phases.
- Foundational claims should be treated as untrusted until the repo proves them.
- The first authoritative rewrite artifacts should be produced in this order:
  foundational constraint schema and audit output, evidence catalog and review
  packet schema, plugin dossier template and source-trust rules, then the
  plan-item and phase-exit schema.
- The governance system must remain usable by a single human reviewer. This is a
  first-class requirement, not a convenience.
- Every canonical governance artifact should have explicit ownership,
  supersession rules, and update triggers to prevent silent drift after the
  initial rewrite.
