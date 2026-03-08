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

## Validation

- `uv run ruff check .`
- `uv run pytest`
