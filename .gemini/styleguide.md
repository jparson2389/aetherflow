# Aetherflow Python Review Guide

This file is for **code review guidance** inside `.gemini/`. It is not the
authoritative source of repository rules.

For canonical project policy, structure, tooling, and constraints, defer to:

- `AGENTS.md`
- `pyproject.toml`

If this file conflicts with either of those, follow the repo files.

---

## Review Goal

When reviewing Python changes in this repository, prioritize:

- correctness
- maintainability
- consistency with repo tooling
- architectural fit
- testability
- minimal, safe changes

Do not suggest stylistic preferences that conflict with the repo’s configured
tooling.

---

## Source of Truth for Reviews

Assume the following are already defined by the repo and should be enforced in
reviews:

- Python version: 3.12+
- Environment/tool runner: `uv`
- Formatter/linter: Ruff
- Test runner: pytest
- Main Python package root: `src/aetherflow/`
- Tests live in: `tests/`

Reference the actual repo config rather than generic Python conventions.

---

## What Reviewers Should Check

### 1. Repo placement and boundaries

Flag code if it violates project structure.

Review for:

- Python application code outside `src/aetherflow/`
- tests outside expected test structure without good reason
- generated proto/grpc files being hand-edited
- logic being added in the wrong layer or wrong subsystem

Do not recommend moving code unless the move clearly aligns with the existing
repo structure in `AGENTS.md`.

### 2. Tooling alignment

Reviews should align with configured tooling, not generic defaults.

Check for:

- suggestions that conflict with Ruff formatting or lint rules
- suggestions that ignore `line-length = 88`
- use of patterns already excluded or intentionally configured in the repo
- commands that use bare `python` or `pip` instead of `uv`

Prefer review comments like:

- “This should match the Ruff-configured style.”
- “Use the project’s `uv` workflow here.”

Not:

- “PEP 8 says …” when the repo config already defines the standard.

### 3. Types and signatures

Prefer explicit, reviewable interfaces.

Check for:

- missing argument type hints on public functions
- missing return annotations on public functions
- vague or overly broad types where a clearer type is practical
- path handling that should use `pathlib.Path`

Do not force unnecessary complexity in typing for small private helpers.

### 4. Docstrings and public API clarity

Check public-facing code for:

- missing or weak docstrings where the interface is non-obvious
- docstrings that do not match actual behavior
- unclear parameter or return behavior
- misleading names that make docstrings harder to trust

Prefer concise, accurate Google-style docstrings where they add value. This is
consistent with the repo guidance.

### 5. Imports and module hygiene

Check for:

- broken import grouping
- unnecessary imports
- unused imports
- local imports that should be module-level
- relative import usage that conflicts with repo conventions

Prefer absolute imports and clean module boundaries.

### 6. Error handling

Check for:

- broad `except Exception` without a strong boundary reason
- swallowed exceptions
- vague error messages
- invalid input paths that should fail earlier
- retry or fallback logic that hides real failures

Prefer specific exceptions and actionable failure messages.

### 7. Logging and observability

Check for:

- noisy logs with little debugging value
- inconsistent logging style within the same subsystem
- logs missing useful context
- logs leaking sensitive or unnecessary data

Match the existing subsystem’s logging approach rather than inventing a new one.

### 8. Test quality

Treat tests as first-class review targets.

Check for:

- missing tests for meaningful behavior changes
- brittle tests tied to implementation details
- tests that depend on machine-specific state
- tests that should use mocks or `tmp_path`
- assertions that are too weak to prove behavior

Prefer hermetic tests that demonstrate real behavior, not just import success or
file existence. This matches the repo’s verification philosophy.

### 9. Architecture fit

Review for consistency with project architecture, not just local code quality.

Check for:

- code crossing boundaries that should stay separate
- duplicated logic where a canonical service or module already exists
- review suggestions that bypass established contracts
- changes that quietly undermine plugin, IPC, proto, or package boundaries

If a change appears locally convenient but architecturally wrong, call that out.

---

## Review Comment Style

Comments should be:

- specific
- actionable
- minimal
- grounded in repo rules or concrete behavior

Prefer:

- “This belongs under `src/aetherflow/...`, not at repo root.”
- “This should use the repo’s `uv run pytest` workflow.”
- “Ruff is authoritative here; this formatting suggestion should follow config.”
- “This test does not prove behavior yet; it only checks file presence.”

Avoid:

- generic style-policing
- personal preference comments
- recommending tools the repo does not use
- repeating rules already enforced automatically unless the diff is fighting them

---

## Default Review Priorities

When time is limited, prioritize in this order:

1. correctness
2. architecture and boundary compliance
3. test adequacy
4. type/interface clarity
5. maintainability
6. style consistency already defined by tooling

---

## Reviewer Constraints

Do not:

- invent new repo policy in this file
- override `AGENTS.md`
- override `pyproject.toml`
- recommend hand-formatting against Ruff
- recommend editing generated proto/grpc Python files
- recommend workflows based on bare `python` or `pip`

---

## Practical Review Heuristic

For each Python diff, ask:

- Is it in the right place?
- Does it fit the existing architecture?
- Does it follow configured tooling?
- Are the interfaces typed and clear?
- Is error handling specific and useful?
- Are tests proving behavior?
- Is the change minimal and maintainable?

If yes, it is likely aligned with the project.
