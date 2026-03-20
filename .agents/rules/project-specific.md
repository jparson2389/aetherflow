---
trigger: always_on
---

# Project Instructions (Aetherflow)

## 🛠 Environment & Runtime

- **Python**: `3.12`
- **Manager**: [uv](https://github.com/astral-sh/uv)
- **Venv**: Always use `.venv/` (created via `uv sync`).
- **Execution**: Always prefix commands: `uv run <command>`.

## Project Structure & File Locations

- **Rule**: Project structure is authoritative here. Agents must follow this layout even if legacy files exist elsewhere.
- **Separation**:
  - Source structure = development code (agents write here).
  - Automation structure = generated outputs (tools only).
  - Distribution structure = final packaged runtime (zip output).

- **Source (Development)**
  - `src/aetherflow/` → main Python package.
    - `core/` → runtime orchestration, plugin manager, shared logic.
    - `proto/` → generated Python protobuf/gRPC stubs; tool-managed only.
    - `ui/` → PySide6 UI shell and panels.
    - `vision/` → capture + CV interfaces.
    - `input/` → input abstractions.
    - `output/` → output abstractions.
    - `plugins/` → Python plugin interfaces/loaders.
  - `proto/` → `.proto` definitions (authoritative source).
  - `assets/` → icons, themes, UI assets.
  - `include/` → native headers/contracts (if used).
  - `host/` → native host/runtime bridge (if used).
  - `docs/` → documentation.
  - `tests/` → test code.
  - `tools/` → automation scripts and developer tooling.

- **Automation / Generated Output**
  - `state/` → automation state, plan execution data.
  - `logs/` → runtime and automation logs.
  - `build/` → temporary build artifacts.
  - `dist/` → packaging staging output.
  - Agents must NOT create new automation folders outside these.
