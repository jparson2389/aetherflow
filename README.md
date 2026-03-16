# Aetherflow

Aetherflow is a Windows-first controller adapter host built around a microkernel
plugin model. The canonical Python package root is `src/aetherflow/`, native C++
artifacts belong under repo-root `host/` and `include/`, and the authoritative
gRPC contracts live in `proto/`.

## Current Foundation

- Native plugin ABI contract: `include/plugin_system.hpp`
- Native host boundary: `host/`
- Control-plane proto: `proto/capture.proto`
- Shared memory contract: `src/aetherflow/core/shared_memory_layout.py`
- Development entrypoint: `src/aetherflow/main.py`

## Documentation

- Product requirements: `docs/PRD.md`
- Implementation plan: `docs/PLAN.md`
- System architecture overview: `docs/architecture/system_overview.md`
- Requirements coverage snapshot: `docs/requirements-report.md`

## Getting Started

Environment and tooling are Windows 11 + PowerShell with Python managed by `uv`:

- Sync dependencies: `uv sync`
- Create a local `.env` from `.env.example` for developer-specific settings
- The application loads `.env` automatically on startup via `uv run aetherflow`
- Launch the main application (CLI/GUI entrypoint): `uv run aetherflow`

## Validation And Quality Gates

Run the core validation commands before marking work complete:

- Lint: `uv run ruff check .`
- Tests: `uv run pytest`
- Combined quality gate (lint, tests, and native build harness):  
  `pwsh -ExecutionPolicy Bypass -File .cursor/workflows/check-quality.ps1`
