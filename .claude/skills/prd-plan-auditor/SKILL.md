---
name: prd-plan-auditor
description: Compare the current implementation state of the Aetherflow project against docs/PRD.md and docs/PLAN.md and write a structured alignment report into the logs folder. Use when checking PRD/plan coverage, drift, or execution readiness.
---

# PRD / Plan Auditor

## Purpose

This skill guides the agent to:

- Read the **product requirements** (`docs/PRD.md`) and **implementation plan** (`docs/PLAN.md`).
- Inspect the **current state of the codebase and tests**.
- Write a concise, structured **alignment report** to the `logs/` directory.

The goal is to quickly understand:

- What parts of the PRD and PLAN appear implemented and validated.
- What is partially implemented or untested.
- What appears missing or out of scope in the current code.

---

## When to Use

Use this skill when:

- You want a **snapshot** of how well the codebase matches the PRD and PLAN.
- You are preparing for a **review, milestone, or release gate**.
- You suspect **scope drift** or plan divergence and want evidence.

This skill is read-only apart from writing a markdown report under `logs/`.

---

## Inputs and Locations

- **Requirements document**: `docs/PRD.md`
- **Plan document**: `docs/PLAN.md`
- **Source code**: primarily under:
  - `src/aetherflow/`
  - `host/`, `include/` (native boundaries)
  - `proto/` (contracts)
- **Tests**: under `tests/` (unit, integration, contracts, UI, etc.).
- **Existing logs & reports** (optional signals):
  - `logs/plan_execution_*.log`
  - `logs/quality-gate.log`
  - `logs/verify-requirements-evidence.md`

If any of these files are missing, note that explicitly in the report instead of failing.

---

## High-Level Workflow

When this skill is invoked, follow these steps:

1. **Load PRD and Plan**
2. **Scan implementation surface**
3. **Map PRD/PLAN items to evidence in code/tests**
4. **Identify gaps, risks, and drift**
5. **Write a structured report to `logs/`**
6. **Summarize results back to the user**

Keep the report **concise, factual, and evidence-backed**.

---

## 1. Load PRD and Plan

1. Use `Read` to load:
   - `docs/PRD.md`
   - `docs/PLAN.md`
2. From these docs, extract a **flat list of items** for tracking, such as:
   - Features or capabilities
   - Non-functional requirements (performance, security, platform support)
   - Milestones or phases from the plan

Represent them conceptually as:

- `PRD items`: numbered or titled sections that describe behaviors/outcomes.
- `Plan tasks`: steps or milestones describing implementation and validation.

You do not need to echo the full documents; just capture enough structure to reason about coverage.

---

## 2. Scan Implementation Surface

Use `Glob` and `Read` to build an overview of the current implementation:

- **Python / core code**:
  - `src/aetherflow/**`
  - Look for modules that correspond to PRD sections (e.g., capture, resources, entitlements, diagnostics).
- **Native / host and contracts**:
  - `host/**`, `include/**`, `proto/**`
  - Note key entrypoints and boundaries (e.g., plugin ABI, capture pipeline, RPC endpoints).
- **Tests**:
  - `tests/**`
  - Group by type where possible (unit, integration, contracts, UI, e2e).

You do not need a full inventory; focus on **high-signal modules and tests** that clearly correspond to PRD/PLAN concepts.

---

## 3. Map PRD / Plan Items to Evidence

For each major PRD and PLAN item you extracted:

1. **Search for corresponding implementation**
   - Use `Grep`/`Glob` to find modules, classes, or functions whose names or docstrings clearly relate to the item.
   - Look for configuration, workflows, or scripts in `.cursor/workflows/` that implement parts of the plan.
2. **Search for corresponding tests**
   - Use `Grep` over `tests/**` for names or keywords matching the item.
   - Prefer tests under `tests/contracts/`, `tests/integration/`, and `tests/e2e/` for higher-level coverage signals.
3. For each item, classify coverage as:
   - **Implemented & tested**: clear code + tests that exercise the behavior.
   - **Implemented, weakly tested**: code present, only light or indirect tests.
   - **Planned only**: appears in PLAN but no obvious implementation.
   - **Missing / unclear**: in PRD but not clearly in PLAN or code.

Be explicit about **evidence** (file names, class/function names, test names) without pasting large code blocks.

---

## 4. Identify Gaps, Risks, and Drift

From the mappings:

- **Gaps**:
  - PRD items with no corresponding implementation or tests.
  - PLAN tasks not reflected in the current codebase.
- **Risks**:
  - Critical features with only partial or indirect test coverage.
  - Areas where implementation appears to diverge from the PRD description.
- **Drift**:
  - Functionality present in the code that is **not** described in PRD/PLAN (possible scope creep).

Keep this analysis descriptive, not speculative:

- Point to **where** you see the mismatch.
- Avoid asserting intent; instead phrase as “appears to”, “likely”, or “may indicate”.

---

## 5. Write the Report to `logs/`

Write a markdown report to the `logs/` directory with a filename like:

- `logs/prd_plan_audit_YYYY-MM-DD.md`

Use this template:

```markdown
# PRD / Plan Alignment Report – YYYY-MM-DD

## Inputs
- PRD: docs/PRD.md
- Plan: docs/PLAN.md
- Code scanned: [high-level paths]
- Tests scanned: [high-level paths]

## Summary
- Overall alignment: [high-level statement]
- Key implemented & tested areas: [short bullets]
- Key gaps or risks: [short bullets]

## Coverage by Item

### [Item 1 Title]
- Source: [PRD section / PLAN section]
- Implementation evidence: [files / modules / brief descriptions]
- Test evidence: [test files / test names]
- Status: Implemented & tested | Implemented, weakly tested | Planned only | Missing / unclear
- Notes: [optional clarifications]

### [Item 2 Title]
...

## Gaps and Risks
- [Gap/risk 1 with evidence]
- [Gap/risk 2 with evidence]

## Potential Next Steps
- [Concrete action 1, e.g., "Add integration tests for X"]
- [Concrete action 2]
```

Prefer **short bullets** and **concrete references** over long prose.

---

## 6. Summarize Back to the User

After writing the report:

1. Confirm the **report file path** and name.
2. Provide a brief summary including:
   - Overall alignment (e.g., “most core capture features implemented and tested; diagnostics and admin flows partially covered”).
   - Count or rough proportion of items in each status bucket.
   - 2–5 key gaps or risks.
3. Offer to:
   - Drill into specific items.
   - Help translate gaps into new PLAN tasks or tickets.

Do **not** paste the entire report into the conversation unless the user explicitly asks; reference the file instead.

