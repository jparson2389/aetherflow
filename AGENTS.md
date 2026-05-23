---
description:
alwaysApply: true
---

# Aetherflow AI Coding Rules & Standards (v4)

## Project Overview

Aetherflow is a Windows-first controller adapter host with a microkernel
plugin architecture. The core system is built in C++20 for the host and
plugin environment, communicating with Python 3.12 workers and a PySide6
(6.9.x) UI strictly via IPC: gRPC for the control plane and shared memory
for frame data. **C++ and Python never share a process.**

`Aetherflow.exe` is the supervisor of record. The PySide6 shell is a durable
client and rendering surface that must remain alive when plugins or workers
fail; Python workers and vision/script workloads stay out of process.

### Canonical architecture sources

These docs are authoritative. Do not restate or contradict them in code,
docs, or PRs — point to them and align with them.

- `docs/architecture/runtime-authority-decision.md` — host-authoritative
  supervision model, shell durability, failure-domain isolation.
- `docs/architecture/delivery-runtime-layout.md` — packaged runtime tree,
  source-area role mapping, and artifact source-of-truth mapping.
- `docs/architecture/delivery-architecture-alignment-notes.md` — PRD
  extraction, AGENTS conflict resolutions, Python module classification
  (shell-only / worker-helper / transitional), and stub disposition.
- `docs/PRD.md` and `docs/PLAN.md` — product requirements and execution plan.
- `proto/capture.proto` — frozen control-plane contract.

## Repository Structure

- `host/` — C++ host and plugin native code only; supervisor of record,
  plugin lifecycle authority, and IPC endpoints.
- `include/` — C++ headers; public ABI and contract definitions.
- `proto/` — `.proto` definitions (authoritative). `proto/capture.proto`
  is **frozen**.
- `src/aetherflow/` — all Python 3.12 logic.
  - `core/` — shared logic, IPC clients/adapters, and transitional
    Python integration. Not the supervisor of record.
  - `core/ipc/` — Python-side client for the frozen `CaptureControl`
    surface (host endpoints).
  - `proto/` — generated gRPC stubs (`*_pb2.py`, `*_pb2_grpc.py`); never
    hand-edit.
  - `ui/` — PySide6 shell, panels, router, status HUD models.
  - `vision/`, `input/`, `output/`, `plugins/` — feature areas; see
    `delivery-architecture-alignment-notes.md` §2.9 for module classification.
- `assets/` — icons, themes, UI assets.
- `docs/` — engineering docs.
- `tests/` — `unit/`, `integration/`, `contracts/` (C++/Python boundary
  validation), `ui/`.
- `tools/` — development-only automation and validation scripts; not shipped.

> Never modify dev tooling at the repo root as part of feature/codegen work.
> Never create new top-level folders without explicit approval.
> Never duplicate a repo-owned file into a second location when a canonical
> path exists.

## Tech Stack & Conventions

- C++20 only under `host/` and `include/`.
- Python 3.12 only under `src/aetherflow/`.
- PySide6 6.9.x for UI, in `src/aetherflow/` only.
- UV is the only way to invoke Python: `uv run ...`. Never `pip`, never
  bare `python`.
- Ruff is authoritative for Python lint/format: `uv run ruff check`,
  `uv run ruff format`.
- Pytest is required: `uv run pytest`. **TDD is mandatory** — write tests
  first.

### Dependencies

Three groups exist. Never add, remove, or change a dependency without
human approval.

**Runtime:**

- `cryptography>=46.0.5`
- `grpcio>=1.78.0`
- `grpcio-tools>=1.78.0`
- `loguru>=0.7.3`
- `mss>=10.1.0`
- `numpy>=2.4.3`
- `opencv-python>=4.13.0.92`
- `protobuf>=6.33.5,<7.0.0` — upper bound is intentional; do not remove
- `pydantic>=2.12.5`
- `pydantic-settings>=2.13.1`
- `pynput>=1.7.7` — approved for KBM input plugin (AF-02-01)
- `pyside6==6.9.1` — pinned exactly
- `python-dotenv>=1.2.2`
- `pyyaml>=6.0.3`

**Dev** (tooling only — not available in application code):
`bandit>=1.9.4`, `detect-secrets>=1.5.0`, `pip-audit>=2.10.0`,
`pytest>=9.0.2`, `ruff>=0.15.6`.

**Automation** (orchestration tooling only — not available in application
code): `openai>=2.28.0`, `anyio>=4.0.0`.

### Environment Bootstrap

- Install/sync with `uv sync`.
- If `PATH` is not normalized, use the explicit local `uv` binary with a
  writable cache, e.g.
  `env PATH=/home/auto_23/.local/bin:$PATH UV_CACHE_DIR=/tmp/aetherflow-uv-cache /home/auto_23/.local/bin/uv ...`.

### Pytest Configuration

- `testpaths: tests/`, `python_files: test_*.py`
- `pythonpath: src and repo root` — both are on the path; do not assume
  imports require full package prefixes.
- `addopts: -ra -q`
- Always run as `uv run pytest`.

## Repo Automation

- Use `uv run python -m tools.check_quality` for the repo-owned quality
  gate; it runs scoped `ruff check --fix`, scoped `ruff format`, and
  `pytest`, and writes `logs/quality-gate.log`.
- Use `uv run python -m tools.build_assets` to regenerate generated
  proto/gRPC modules from `proto/*.proto` and Qt UI modules from
  `assets/ui/*.ui`.
- Use `uv run python -m tools.export_diagrams` to export Mermaid
  diagrams from docs into `assets/` when architecture docs change.
- Use `uv run python -m tools.plan_exec --reconcile-only` to deterministically
  reconcile `state/plan_state.json` against repo evidence without LLM
  execution; `--state-only` is a legacy alias.
- Use `uv run python tools/plan_exec_report.py` to generate a post-run
  summary from the latest `logs/plan_execution_*.log` file.
- Post-edit hooks under `.github/hooks/` run
  `./scripts/format-changed-files.sh`, `./scripts/run-related-tests.sh`,
  `./scripts/scan-secrets.sh`, `./scripts/block-dangerous.sh`, and
  `./scripts/inject-context.sh`. The SessionStart hook
  (`scripts/inject-context.sh`) injects this AGENTS.md into the model's
  context — there is no separate `CLAUDE.md`; this file is the single
  source.

## Agent skills

### Issue tracker

Issues live in GitHub Issues for `jparson2389/aetherflow`. See
`docs/agents/issue-tracker.md`.

### Triage labels

Skills use the repo-aligned GitHub label vocabulary. See
`docs/agents/triage-labels.md`.

### Domain docs

This repo uses single-context domain docs at `CONTEXT.md` and system ADRs under
`docs/adr/`. See `docs/agents/domain.md`.

## Code Style Rules

### Naming

- `snake_case` for Python modules, functions, variables.
- `PascalCase` for Python classes.
- `UPPER_SNAKE_CASE` for constants.
- Use clear, explicit names.

### Imports

- stdlib → third-party → local. One blank line between groups.
- Never use relative imports outside `src/aetherflow/`.

### Type/Style

- All functions, methods, and classes need full type hints and Google-style
  `"""` docstrings (`Args:`, `Returns:`, `Raises:`).
- Never hand-format; Ruff is authoritative.

```python
def foo(x: int) -> bool:
    """Check whether x is valid.

    Args:
        x: The value to check.

    Returns:
        True if x is positive.
    """
```

### Ruff (canonical, enforced via `pyproject.toml`)

- target-version: py312
- line-length: 88
- fix: true
- select: F, E, I, UP, B, RUF, D, ARG, PTH
- ignore: E203, D203, D213, D300, Q002, E501, D100
- format: quote-style='single', line-ending=lf, docstring-code-format=true
- isort: known-first-party=["aetherflow", "tools"], combine-as-imports=true
- per-file ignores: `tools/**/*.py`: D, T201; `tests/**/*.py`: D;
  `src/**/__init__.py`: D104
- exclude: `*_pb2.py`, `*_pb2_grpc.py`, `.venv`, `build`, `.claude`, `.tmp`

**Bandit:** level=medium, confidence=high, skips B101/B104/B608.

**Pyright:** typeCheckingMode=basic, include=`src`, `tools`,
exclude=`src/aetherflow/proto`.

### Generated Artifacts

Never lint, format, or edit generated proto/gRPC modules. Regenerate
them with `uv run python -m tools.build_assets`.

## Architecture Patterns

### Runtime authority

`Aetherflow.exe` is the supervisor of record. See
`docs/architecture/runtime-authority-decision.md` for the decision and
its consequences. Concrete implications for code under review:

- Supervision authority, plugin lifecycle authority, and IPC endpoint
  ownership live in `host/` and `include/`.
- `src/aetherflow/core/worker_supervisor.py` is a **read-only host-state
  view**, not a supervisor. Do not add lifecycle decisions there.
- `src/aetherflow/core/ipc/` is the Python client for the frozen
  `CaptureControl` surface; shell/admin/worker consumers reach host state
  through it, not through direct in-memory calls.
- The PySide6 shell must survive plugin and worker failures and render
  host-reported state rather than infer it.

### IPC boundary

```
PySide6 UI  ─────┐
                 │  Python (src/aetherflow/)
Python workers ──┘
        ↕  gRPC (proto/capture.proto) + shared memory only
C++ host (host/) + plugins (include/plugin_system.hpp)
```

- `proto/capture.proto` is **frozen**; validated by
  `host/native_harness.cpp` and `tests/contracts/test_native_harness.py`.
- Generated stubs go in `src/aetherflow/proto/` only.
- Shared memory frame layout is in
  `src/aetherflow/core/shared_memory_layout.py`.

### Entitlement state machine

- Canonical implementation: `src/aetherflow/core/entitlements.py`
- States: `LOADED`, `ELIGIBLE`, `LOCKED`, `GRACE`.
- **Only** call `EntitlementStore.evaluate(...)`. Never reimplement,
  duplicate, or inline the logic.
- Never add, remove, or change states/transitions without explicit human
  sign-off.
- Tests: `tests/unit/test_entitlements.py`,
  `tests/integration/test_plugin_catalog_locking.py`,
  `tests/ui/test_status_hud.py`.

## Packaging & Delivery

The packaged Windows runtime tree, source-area role mapping, and
artifact source-of-truth mapping are defined in
`docs/architecture/delivery-runtime-layout.md`. **Consult it before any
packaging, staging, or layout decision; do not infer from memory.**

Load-bearing rules agents must not violate (full detail in that doc):

- Root `Aetherflow.exe` is the wrapper/bootstrap. `lib/Aetherflow2.exe`
  is the primary runtime. Preserve both as distinct roles; never
  collapse or duplicate them.
- `plugins/` is the primary plugin DLL load tree. `lib/plugins/` is a
  runtime-support subtree, **not** a replacement for `plugins/`.
- Plugin translations canonicalize at
  `lib/translations/plugins/<PluginName>/`. Root-level `.qm` files in
  `plugins/` are legacy and normalize there.
- Managed Python runtimes, `uv.exe`, workload roots (e.g. `cv/`), and
  `.aenv` environments live under
  `%LOCALAPPDATA%/AetherflowProject/Aetherflow/python/`. This is mutable
  managed state — **never** part of the packaged app root, and `.aenv`
  must never be staged into `dist/`.
- During normal development, prefer repo-owned tooling in `tools/`.
  `scripts/` in the packaged app may exist as an empty directory; do not
  add dev helpers there.

## Do's and Don'ts

### Do

- `uv run` for all Python commands.
- Write tests first.
- Add type hints and Google-style `"""` docstrings to all Python code.
- Run `uv run python -m tools.check_quality` before marking work done,
  or at minimum `uv run ruff check && uv run pytest`.
- Treat `proto/capture.proto` as **FROZEN**.
- Always call `EntitlementStore.evaluate(...)` for entitlement checks.
- Python only in `src/aetherflow/`; C++ only in `host/` or `include/`.

### Don't

- Never modify `proto/capture.proto` or any frozen contract without
  explicit human sign-off.
- Never load a premium DLL without an entitlement token.
- Never execute an unsigned artifact.
- Never bypass or inline entitlement logic.
- Never hand-edit or move generated gRPC stubs.
- Never put Python code outside `src/aetherflow/`.
- Never use C++/Python embedding, ctypes, or similar in-process hacks.
- Never create new top-level folders or duplicate canonical files
  without explicit approval.

## Testing & Quality

- `uv run pytest` — TDD mandatory.
- Test files: `test_*.py`; contract tests under `tests/contracts/`.
- Required coverage: entitlement transitions, plugin catalog locking,
  status HUD entitlement rendering.
- Tests must be **hermetic** — mock processes, use pytest `tmp_path`,
  no real signing certs, no live FS writes outside the temp area.
- Lint and tests must both pass for build/merge.
- Evidence-based requirements verification:
  `uv run python -m tools.verify_requirements` (add `--debug` only when
  you need heuristic output).
- Golden regression for the verification heuristics:
  `uv run pytest tests/contracts/test_verify_requirements_evidence.py`.

## Common Pitfalls

- **Modifying `proto/capture.proto`** — frozen; enforced by
  `host/native_harness.cpp`.
- **Running `python` or `pip` directly** — always `uv run`.
- **Hand-editing generated gRPC stubs** — regenerate only.
- **Placing Python outside `src/aetherflow/`** — breaks build.
- **Assuming in-process embedding** — IPC only.
- **Reimplementing or inlining entitlement resolution** — only
  `EntitlementStore.evaluate(...)`.
- **Treating `worker_supervisor.py` as authoritative** — it is a
  read-only host-state view; supervision authority lives in `host/`.
- **Producing valid JSON with broken Python** — every used symbol must
  be imported in its file; do not assume cross-file scope.
- **Tests that depend on real environment state** — must be hermetic;
  no real signing, no real FS side effects.

---

### End of Aetherflow AI Coding Rules & Standards (v4)
