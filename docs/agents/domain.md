# Domain Docs

How the engineering skills should consume this repo's domain documentation when
exploring the codebase.

## Before exploring, read these

- `CONTEXT.md` at the repo root for the project glossary, boundaries, and
  canonical documents.
- `docs/adr/` for accepted architecture decisions that apply across the system.
- `docs/architecture/` for the canonical runtime authority, packaging, and
  delivery architecture documents referenced from `CONTEXT.md`.
- `docs/PRD.md` and `docs/PLAN.md` when a task touches requirements,
  implementation sequencing, or frozen contracts.

If a topic has both an ADR and a detailed architecture note, treat the ADR as
the decision record and the architecture note as the operational detail.

## File structure

This is a single-context repo:

```text
/
├── CONTEXT.md
├── docs/
│   ├── adr/
│   │   └── 0001-runtime-authority.md
│   └── architecture/
└── src/aetherflow/
```

## Use the glossary's vocabulary

When output names a domain concept in an issue title, plan, hypothesis, test, or
refactor proposal, use the term as defined in `CONTEXT.md`. If the concept is
missing, note the gap rather than inventing parallel terminology.

## Flag ADR conflicts

If an output contradicts an accepted ADR, surface the conflict explicitly and do
not silently override it.
