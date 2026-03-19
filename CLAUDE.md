# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Dependencies
uv sync                                   # Install all deps
uv sync --group dev                       # Include dev tools
uv sync --group automation                # Include automation tools

# Run
uv run aetherflow                         # Launch main entrypoint

# Lint & format
uv run ruff check .                       # Lint (auto-fixes enabled)
uv run ruff format .                      # Format

# Test
uv run pytest                             # All tests
uv run pytest tests/unit/                 # Unit tests only
uv run pytest tests/unit/test_foo.py -k "test_bar"  # Single test

# Security
uv run bandit -r src/                     # Security audit
uv run detect-secrets scan                # Secret scanning

# Quality gate (combined lint + test + security)
pwsh -ExecutionPolicy Bypass -File .cursor/workflows/check-quality.ps1

# Native C++ build
pwsh -ExecutionPolicy Bypass -File scripts/build-native.ps1
```

## Architecture

Aetherflow is a **Windows-first controller adapter host** with a microkernel plugin architecture. The critical constraint: **C++ and Python never share a process** — they communicate only via gRPC (control plane) and shared memory (frame data).

### Boundary layers

```
PySide6 UI  ─────┐
                  │  Python (src/aetherflow/)
Python workers ──┘
        ↕  gRPC (proto/capture.proto) + shared memory only
C++ host (host/) + plugins (include/plugin_system.hpp)
```

### Key modules

| Path                                          | Role                                                                            |
| --------------------------------------------- | ------------------------------------------------------------------------------- |
| `src/aetherflow/core/entitlements.py`         | Canonical entitlement state machine — ONLY call `EntitlementStore.evaluate()`   |
| `src/aetherflow/core/runtime_state.py`        | User-visible states: RUNNING, DEGRADED, RECOVERING, FAILED, LOCKED, GRACE       |
| `src/aetherflow/core/services.py`             | `AppServices` — shared runtime container (entitlements, trust verifier, roles)  |
| `src/aetherflow/core/worker_supervisor.py`    | Health tracking and restart budgets for Python workers                          |
| `src/aetherflow/core/shared_memory_layout.py` | Ring buffer contract and pixel formats for frame exchange                       |
| `src/aetherflow/plugins/`                     | Catalog, manifest, registry, and trust verifier                                 |
| `src/aetherflow/ui/`                          | PySide6 shell, router, and status HUD models                                    |
| `proto/capture.proto`                         | **Frozen** gRPC control-plane contract — never modify without explicit approval |
| `src/aetherflow/core/ipc/`                    | Generated gRPC stubs (`*_pb2.py`, `*_pb2_grpc.py`) — never hand-edit            |

### Automated plan execution (tools/)

The `tools/` directory contains an AI-driven implementation loop:

- `tools/plan_exec.py` — Main orchestrator that reads `PLAN.md`, selects work items via an LLM PM agent, dispatches to implementation agents, and validates results through a 3-layer gate
- `tools/validation_gate.py` — Layer 1: file existence; Layer 2: command execution (pytest/ruff); Layer 3: PM semantic verification
- `tools/apply_writes.py` — Secure file writer with path allowlist enforcement
- `tools/prompts.py` — Canonical system prompts for all agent roles

Plan state persists to `state/plan_state.json`. Per-run logs go to `logs/plan_execution_*.log`. Verification artifacts land in `logs/verification/<item_id>.json`.

### Constraints enforced by AGENTS.md

- **UV only** — never `pip` or bare `python`
- **TDD** — write tests first
- **Double-quoted docstrings** — `"""` not `'''`; enforced by `ruff format` (formatter always uses `"""` per Black convention)
- **Entitlements** — never inline entitlement logic; always `EntitlementStore.evaluate(...)`
- **Dependencies** — never add/remove without human approval (3 groups: runtime, dev, automation)
- **proto/ is frozen** — `proto/capture.proto` is the authority; re-generate stubs with grpcio-tools, never hand-edit

See `AGENTS.md` for complete coding standards.
