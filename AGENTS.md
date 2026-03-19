---
description:
alwaysApply: true
---

# Aetherflow AI Coding Rules & Standards (v3)

## Project Overview

Aetherflow is a Windows-first controller adapter host utilizing a microkernel plugin architecture. The core system is built in C++ (C++20) for the host/server and plugin environment, communicating strictly with Python (Python 3.12) workers and a PySide6 (6.9.x) UI via IPC only. There is **never** in-process embedding—C++ and Python interact only through gRPC control-plane services (as defined in frozen contracts) and shared memory for frame data. These boundaries are enforced structurally and by automated verification.

Development is driven by an automated AI loop orchestrated with OpenAI Python SDK, executing against a PRD and implementation plan. Strict code generation, review, and validation rules apply.

### Repository Structure

- `host/`: C++ host and plugin native code **only**

- `include/`: C++ header files

- `proto/`: **Authority** for proto contracts, e.g. `proto/capture.proto` (**frozen**)

- `src/aetherflow/`: All Python (3.12) logic, including:
  - PySide6 UI

  - Python workers

  - Generated Python gRPC stubs (`src/aetherflow/proto/` per ASM-01)

  - Shared memory layout

- `docs/`: Engineering docs; e.g. `PLAN.md`, `proto/capture.md`, `breaking-changes/proto.md`

- `tests/`: All tests; contract and integration/unit/UI
  - `tests/contracts/test_native_harness.py`: C++/Python boundary validation

> **NEVER** modify dev tooling at the repo root as part of feature/codegen work.

---

## Tech Stack & Conventions

- C++20 is only under host/ and include/. No exceptions.

- Python 3.12 application code is always under src/aetherflow/. No Python elsewhere.

- PySide6 (6.9.x) for UI—stays in src/aetherflow/ only.

- gRPC contract defined in proto/ (frozen):

- proto/capture.proto is canonical control-plane, strictly enforced.

- Generated Python stubs MUST go in `src/aetherflow/proto/`. Never hand-edit, never move.

- UV is the only way to invoke all Python commands: uv run ...

- Never use pip. Never bare python.

- Ruff is the authority for Python formatting/linting: always run with uv run ruff check.

- Ruff rules and config are binding. See below for full details.

- Pytest for all test execution (uv run pytest).TDD enforced: implement tests first.

- Shared memory for frame data: follow layout in shared_memory_layout.py.

- proto/ is the only authoritative proto source.

- Only place generated gRPC stubs in `src/aetherflow/proto/`. Never modify by hand.

### Dependencies

Three dependency groups exist. Never add, remove, or change a dependency without human approval.

**Runtime:**

- cryptography>=46.0.5

- grpcio>=1.78.0, grpcio-tools>=1.78.0

- loguru>=0.7.3

- mss>=10.1.0

- numpy>=2.4.3

- opencv-python>=4.13.0.92

- protobuf>=6.33.5,<7.0.0 — upper bound is intentional, do not remove it

- pydantic>=2.12.5, pydantic-settings>=2.13.1

- pyside6==6.9.1 — pinned exactly, do not change this pin

- python-dotenv>=1.2.2

- pyyaml>=6.0.3

**Dev group** (dev tooling only — not available in application code):

- bandit>=1.9.4, detect-secrets>=1.5.0, pip-audit>=2.10.0

- pytest>=9.0.2, ruff>=0.15.6

**Automation group** (orchestration tooling only — not available in application code):

- openai>=2.28.0, anyio>=4.0.0

---

### Pytest Configuration

- testpaths: tests/

- python_files: test\_\*.py

- pythonpath: src and repo root (both are on the path — do not assume imports require full package prefixes)

- addopts: -ra -q

- Always run as: uv run pytest

---

## Code Style Rules

### Naming Conventions

### Imports

- Standard lib, then third-party, then local; one blank line between each group.

- **Never** use relative imports outside `src/aetherflow/`.

### Python Type/Style

- **All** functions, methods, and classes:
  - Full type hints on EVERY argument + return.

  - **Docstrings:**
    - **Double-quoted delimiters:** Use `"""` (never `'''`) for all docstrings — `ruff format` enforces this.

    - **Google docstring format:** Use Args:, Returns:, Raises: as in the following example:

    ```python
    def foo(x: int) -> bool:
        """Check whether x is valid.

        Args:
            x: The value to check.

        Returns:
            True if x is positive.
        """

    ```

```

* Always annotate public/exported function/method return types.

* **Never** hand-format code; Ruff is authoritative.

### Ruff Configuration (canonical, enforced via pyproject.toml)

* **target-version:** py312

* **line-length:** 88

* **fix:** true

* **Selected lint rules:**

  * F (Pyflakes), E (pycodestyle), I (isort), UP (pyupgrade), B (flake8-bugbear), RUF, D (pydocstyle), ARG (unused args), PTH (use pathlib)

* **ignore:** E203, D203, D213, D300, Q002, E501, D100

  * D300 + Q002 (formatter uses `"""` for docstrings; these rules would conflict with `ruff format`)

  * D212/D213: Pick D212 multi-line summary, ignore D213

* **Format:**

  * quote-style = 'single'

  * line-ending = lf

  * docstring-code-format = true

* **isort:** known-first-party = \["aetherflow", "tools"\], combine-as-imports = true

* **Per-file ignores:**

  * `tools/**/*.py`: D, T201

  * `tests/**/*.py`: D

  * `src/**/__init__.py`: D104

* **Exclude from Ruff/lint/edit:** `*_pb2.py`, `*_pb2_grpc.py`, `.venv`, `build`

* **Bandit:** Level=medium, confidence=high, skips B101/B104/B608, excludes tests, build, venv, `*_pb2.py`, `*_pb2_grpc.py`

* **Pyright:** typeCheckingMode=basic, include=src/tools, exclude=src/aetherflow/proto

**Generated Artifacts**

* Never lint, format, or edit `*_pb2.py` / `*_pb2_grpc.py` (generated files).

* NEVER touch these files for any reason. Ruff and Bandit enforce this.

---

## Component & Architecture Patterns

* **C++ host/plugins:**

  * Exclusively in `host/` & `include/`, validated at build (see `host/native_harness.cpp`).

  * Contract validation in `tests/contracts/test_native_harness.py`.

* **Python workers/UI:**

  * All logic is in `src/aetherflow/`. No direct embedding of C++.

  * IPC: gRPC control plane (`proto/capture.proto` authority); shared memory (`shared_memory_layout.py`).

* **gRPC boundary:**

  * Generated stubs: `src/aetherflow/proto/` artifacts only, never modify or move.

  * **FROZEN CONTRACT:** `proto/capture.proto` is the authority. Validated by `host/native_harness.cpp` at build.

* **Entitlement State Machine:**

  * Canonical implementation: `src/aetherflow/core/entitlements.py`

  * `EntitlementState`: `LOADED`, `ELIGIBLE`, `LOCKED`, `GRACE`

  * **State resolution:** Only use `EntitlementStore.evaluate(...)`.

  * Do NOT reimplement, duplicate, or inline logic—always call `EntitlementStore.evaluate(...)`.

  * Roles: `RoleName`, `ROLE_CAPABILITIES`, `UserRole` model PRD roles.

  * Integrated in: UI shell/router, plugin catalog, status HUD.

  * Tests: `tests/unit/test_entitlements.py`, `tests/integration/test_plugin_catalog_locking.py`, `tests/ui/test_status_hud.py`

  * Never modify, add, remove, or bypass states/transitions without explicit human sign-off.

---

## Do's and Don'ts

### Do

* Use `uv run` for all Python commands:

  * `uv run ruff check`

  * `uv run pytest`

  * `uv run python ...`

* TDD: Write test files before feature code.

* Add **type hints and Google-format docstrings** (`"""`) to all Python code.

* Run `uv run ruff check && uv run pytest` before marking done.

* Treat `proto/capture.proto` as FROZEN.

* Generated gRPC stubs: always in `src/aetherflow/proto/`, never hand-edit.

* Request approval before any entitlement state machine or frozen contract semantic change.

* Python ONLY in `src/aetherflow/`, C++ ONLY in `host/` or `include/`.

### Don't

* NEVER modify `proto/capture.proto` (or any frozen contract) without explicit human sign-off.

* NEVER load any premium DLL without entitlement token.

* NEVER execute an unsigned artifact.

* Never bypass or inline entitlement logic; always use `EntitlementStore.evaluate(...)`.

* Never add, change, or remove entitlement state or transitions without approval.

* Never hand-edit or move generated gRPC stubs.

* Never put Python code outside `src/aetherflow/`.

* Never use C++/Python embedding, ctypes, or similar hacks.

---

## Testing & Quality

* Use **pytest**: `uv run pytest`

* TDD is mandatory: always implement test first.

* Name test files `test_*.py`, colocate with code or place under `tests/`.

* Contract tests: in `tests/contracts/`

* Test coverage **required** for:

  * All entitlement transitions (`tests/unit/test_entitlements.py`)

  * Plugin catalog locking (`tests/integration/test_plugin_catalog_locking.py`)

  * Status HUD entitlement rendering (`tests/ui/test_status_hud.py`)

* Lint and test must both pass (via `uv run ruff check`, `uv run pytest`) for build loop or merge to succeed.

---

## Common Pitfalls

* **Modifying** `proto/capture.proto` **directly:**

  This is a FROZEN contract, enforced by `host/native_harness.cpp`. Never edit—ask for approval if a change is required.

* **Running** `python` **or** `pip` **directly:**

  Always use `uv run`. Never bypass environment or lockfile management.

* **Hand-editing generated gRPC stubs:**

  Regenerate only; never edit, move, or lint them.

* **Placing Python code outside** `src/aetherflow/`**:**

  Structural enforcement is strict. Violation breaks build.

* **Assuming in-process embedding:**

  C++ and Python communicate only via IPC (gRPC, shared memory).

* **Reimplementing or inlining entitlement resolution:**

  Only call `EntitlementStore.evaluate(...)` for any entitlement check. Never duplicate the logic.

* **Modifying or extending the entitlement state machine without approval:**

  `EntitlementState`, roles, or transitions require human sign-off.

* **NEW:** **Producing valid JSON with broken Python**

  * Problem: Output passes JSON/Pydantic validation but code fails at runtime (missing imports, undefined names, broken tests).

  * Guidance: Every used symbol MUST be imported in its file. Do not assume a symbol from another file in the payload is in scope.

* **NEW:** **Writing tests that depend on real environment state**

  * Problem: Tests that perform real PowerShell signing, need code signing certs, or affect the real FS pass write validation but fail in CI/dev.

  * Guidance: All tests must be hermetic. Mock processes. Use pytest `tmp_path`.

---

**End of Aetherflow AI Coding Rules & Standards (v3)**
```
