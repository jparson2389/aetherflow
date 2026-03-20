---
name: project-docs-author
description: Analyze the current repository and generate or update high-signal project docs such as AGENTS.md and README.md. Use when the user asks to create, refresh, or audit top-level documentation based on the actual codebase, workflows, and guardrails.
---

# Project Docs Author

## Purpose

This skill guides the agent to **inspect the repository first** and then **author or update** high-value documentation:

- `AGENTS.md` (AI assistant persona, guardrails, environment)
- `README.md` (what the project is, how to work with it)
- Optionally `docs/` entrypoints or other top-level docs the repo already uses

The focus is on **concise, accurate, codebase-grounded docs**, not generic boilerplate.

---

## When to Use

Use this skill when:

- The user asks to create or refresh `AGENTS.md`, `README.md`, or similar top-level docs.
- The repo structure or workflows have changed and docs may be stale.
- Bringing a new collaborator (human or agent) onto the project and you want a fresh, trustworthy overview.
- You need to synchronize docs with the actual code (e.g., new commands, directories, or contracts).

Do **not** use this skill for:

- Deep API reference generation for a single module (handle that locally in the conversation).
- Auto-generating docs for third-party dependencies.

---

## High-Level Workflow

Follow this workflow in order:

1. **Discover the repo shape**
2. **Detect existing top-level docs**
3. **Infer core workflows and contracts**
4. **Draft or update `AGENTS.md`**
5. **Draft or update `README.md`**
6. **Summarize changes and next steps for the user**

Always keep docs:

- **Grounded**: Only describe behaviors and workflows that you can infer from code, configs, or existing docs.
- **Concise**: Prefer short sections and bullet lists.
- **Actionable**: Emphasize how to run, test, and extend the project.

---

## 1. Discover Repo Shape

1. Use `Glob` to understand the top-level layout:
   - Look for: `src/`, `host/`, `include/`, `proto/`, `tests/`, `docs/`, `.cursor/`, `.agents/`, `pyproject.toml`, `package.json`, etc.
2. Use `Read` on key files to infer stack and workflows:
   - Python projects: `pyproject.toml`, `src/**/__init__.py`, CLI or entrypoints (e.g. `src/**/main.py`).
   - Native components: headers under `include/`, host binaries or projects under `host/`.
   - RPC/contract layers: files under `proto/` or `api/`.
   - Quality gates: CI configs, `Makefile`, PowerShell workflows in `.cursor/workflows/`, or similar.

Record (mentally) the answers to:

- What is the **primary language and runtime**?
- Where does **application code** live?
- Where do **native or external components** live (if any)?
- How are **tests and linting** run?
- Are there any **existing guardrails or persona files** (e.g. `AGENTS.md`, `.cursor/rules/`)?

You do **not** need to echo this raw scan to the user; use it to drive the docs you write.

---

## 2. Detect Existing Top-Level Docs

1. Use `Glob` / `Read` to check for:
   - `AGENTS.md`
   - `README.md`
   - `docs/**` (e.g. `docs/index.md`, `docs/architecture.md`)
2. For each existing doc:
   - Skim with `Read` to understand what is already documented.
   - Note sections that are still correct vs obviously stale (e.g., old commands, missing directories, wrong stack).

Rules:

- **Preserve correct, specific content** that still matches the codebase.
- **Update or remove** content that is clearly outdated or conflicts with what you see in the repo.
- Avoid duplicating large blocks of information across multiple docs; link or summarize instead.

---

## 3. Infer Core Workflows and Contracts

From the repo scan, infer:

- **How to set up the environment**
  - Package manager(s) and main commands (`uv sync`, `npm install`, etc.).
  - Runtime versions (Python, C++, Node, etc.) if discoverable.
- **How to run quality checks**
  - Linting (`uv run ruff check .`, ESLint, etc.).
  - Tests (`uv run pytest`, `npm test`, etc.).
- **Key contracts and boundaries**
  - Native/host boundaries (e.g. `include/**`, `host/**`).
  - Protocol or API contracts (e.g. `proto/**`).
  - Shared-memory or IPC layouts if clearly defined.

Keep this high level; the goal is to support an accurate **"How this project fits together"** section, not a full spec.

---

## 4. Draft or Update `AGENTS.md`

If `AGENTS.md` exists, treat it as **authoritative guardrails** and update carefully.
If it does not exist, create a new one at repo root.

`AGENTS.md` should answer:

- **Persona**: Who the agent should pretend to be (role, seniority, platform focus).
- **Stack**: Primary languages, frameworks, and tools for this repo.
- **Style and testing**: Expectations about docstrings, typing, testing discipline, logging, etc.
- **Guardrails**: Security, safety, and git hygiene rules specific to this project.
- **Environment**: OS assumptions, shells, package managers, and canonical commands.

When editing:

- **Preserve existing non-conflicting guardrails**.
- Add or adjust bullets when the codebase indicates:
  - Different or additional commands (e.g. new workflows under `.cursor/workflows/`).
  - New language or framework usage.
  - New safety rules (e.g. entitlements, frozen contracts).

Keep sections short and bullet-oriented so agents can scan them quickly.

---

## 5. Draft or Update `README.md`

If `README.md` exists, update it in place; otherwise create one at repo root.

Minimum recommended structure:

1. **Project name and one-line description**
   - Describe what the project does, in one sentence grounded in the codebase.
2. **Architecture overview**
   - Briefly describe the main components and where they live (e.g., “Python package under `src/...`, native host under `host/`, contracts under `proto/`”).
3. **Getting started**
   - Clone and environment setup.
   - Primary install/sync command(s).
4. **Validation / quality gates**
   - How to run linting and tests.
5. **Key contracts and entrypoints**
   - Where to find protocol definitions, host boundaries, and the main runtime entrypoints.

Guidelines:

- Prefer **short paragraphs and bullet lists**.
- When in doubt, link to deeper docs (e.g. `docs/architecture.md`) instead of restating them.
- Only document commands and paths that you have observed via `Read` or `Glob`.

---

## 6. Summarize Changes for the User

After editing docs:

1. List which files you created or updated (e.g. `AGENTS.md`, `README.md`).
2. Summarize changes in a few bullets, focusing on:
   - New or updated environment/quality commands.
   - New architecture or contract descriptions.
   - Any tightened guardrails or persona clarifications.
3. Explicitly call out anything you were **not** sure about and left unchanged.

Do **not** paste entire docs into the summary unless the user explicitly asks; highlight only the most important changes.

---

## Example Usage Pattern

When this skill is invoked because the user asks for updated project docs:

1. Run the discovery steps to map the repo.
2. Skim existing `AGENTS.md` and `README.md` (if present).
3. Bring them in sync with:
   - Actual directory layout.
   - Real quality commands and workflows.
   - Any project-specific guardrails or personas.
4. Present a **brief summary** and optionally offer to show specific sections on request.

This keeps project docs authoritative, minimal, and always in step with the codebase.
