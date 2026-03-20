---
trigger: always_on
---

# Coding Standards (PEP 8 & 3.12 Syntax)

- **Naming**: `snake_case` (functions/vars), `PascalCase` (classes), `UPPER_SNAKE_CASE` (constants).
- **Typing (Modern)**:
  - Use `type Alias = ...` (PEP 695).
  - Use `int | str` instead of `Union`.
  - Use `list[str]` instead of `List`.
- **Imports**: Standard → Third-party → Local. Use absolute imports only.
- **Docstrings**: Use docstrings for all public functions using Google Format.
- **Ruff**: Follow strict <88 character line length.

## Quality Control & Commands

- **Install**: `uv sync`
- **Format**: `uv run ruff format .`
- **Lint & Fix**: `uv run ruff check --fix .`
- **Test**: `uv run pytest`

## Project Specifics

- **Ignore**: Do not lint/format `*_pb2.py` or `*_pb2_grpc.py`.
- **UI**: Convert `.ui` files using `pyside6-uic`.
- **GRPC**: Generate via `uv run python -m grpc_tools.protoc`.

- **Write Rules**:
  - All Python source must live under `src/`.
  - Do not create new top-level folders without explicit approval.
  - If a file already exists in multiple locations, do NOT create another copy.
  - Prefer updating canonical paths instead of duplicating files.

- **Distribution (Runtime ZIP Layout)**:
  - `Aetherflow.exe`
  - `lib/`
  - `plugins/`
  - `assets/`
  - `scripts/`
  - This structure is runtime-only. Agents do NOT write here during normal development.
