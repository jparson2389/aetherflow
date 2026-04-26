# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Environment

- **Dev platform**: WSL2 (Ubuntu) on Windows — shell is `bash`, Python tooling runs natively under Linux
- **Deployment target**: Windows-first (the compiled C++ host and plugins target Windows)
- **PowerShell scripts** (`scripts/*.ps1`) require PowerShell Core (`pwsh`) installed in WSL. Prefer the `uv run python -m tools.*` equivalents for daily dev — they are the canonical cross-platform entry points.
- **Native C++ build** (`scripts/build-native.ps1`) requires MSVC and must be run on Windows or via a Windows build agent; it cannot compile inside WSL.

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

# Build generated assets
uv run python -m tools.build_assets       # Cross-platform (preferred in WSL)
pwsh -ExecutionPolicy Bypass -File scripts/build-assets.ps1  # Requires pwsh in WSL

# Security
uv run bandit -r src/                     # Security audit
uv run detect-secrets scan                # Secret scanning

# Quality gate (combined lint + test + security)
uv run python -m tools.check_quality      # Cross-platform (preferred in WSL)
pwsh -ExecutionPolicy Bypass -File scripts/check-quality.ps1  # Requires pwsh in WSL

# Native C++ build (Windows only — run on Windows build agent, not in WSL)
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
| `host/` and `include/`                        | Native host boundary: supervisor of record, plugin lifecycle authority, IPC     |
| `src/aetherflow/core/worker_supervisor.py`    | Transitional Python-side adapter/client; not the supervisor of record           |
| `src/aetherflow/core/shared_memory_layout.py` | Ring buffer contract and pixel formats for frame exchange                       |
| `src/aetherflow/plugins/`                     | Catalog, manifest, registry, and trust verifier                                 |
| `src/aetherflow/ui/`                          | PySide6 shell, router, and status HUD models                                    |
| `proto/capture.proto`                         | **Frozen** gRPC control-plane contract — never modify without explicit approval |
| `src/aetherflow/proto/`                       | Generated gRPC stubs (`*_pb2.py`, `*_pb2_grpc.py`) — never hand-edit            |

### Packaged runtime model

- Root `Aetherflow.exe` is the wrapper/bootstrap executable.
- `lib/Aetherflow2.exe` is the primary runtime executable.
- `plugins/` is the primary plugin DLL load directory.
- `lib/plugins/` is a runtime-support subtree, not a replacement for
  `plugins/`.
- Plugin translations live under `lib/translations/plugins/<PluginName>/`.
- Managed Python runtimes, `uv.exe`, workload roots such as `cv/`, and
  `.aenv` environments live under
  `%LOCALAPPDATA%/AetherflowProject/Aetherflow/python/`, not inside the
  packaged app root.

### Tooling scope

- `tools/` is development-only, non-shipping infrastructure.
- Do not spend product-delivery effort in `tools/` unless the task is explicitly about packaging, validation, or repo maintenance.
- Default implementation focus is the app itself: `host/`, `include/`, `src/aetherflow/`, `proto/`, packaged runtime docs, and tests that validate shipped behavior.

### Automated plan execution (tools/)

The `tools/` directory contains repository automation and validation helpers:

- `tools/plan_exec.py` — Main orchestrator that reads `PLAN.md`, selects work items via an LLM PM agent, dispatches to implementation agents, builds repo-owned assets, and validates results through a 3-layer gate; it also supports deterministic `--reconcile-only` state sync without invoking an LLM
- `tools/validation_gate.py` — Layer 1: file existence; Layer 2: command execution (pytest/ruff); Layer 3: PM semantic verification
- `tools/apply_writes.py` — Secure file writer with path allowlist enforcement
- `tools/prompts.py` — Canonical system prompts for all agent roles

Plan state persists to `state/plan_state.json`. Treat it as an executor checkpoint, not authoritative proof of repo reality. Per-run logs go to `logs/plan_execution_*.log`. Verification artifacts land in `logs/verification/<item_id>.json`.

### Constraints enforced by AGENTS.md

- **UV only** — never `pip` or bare `python`
- **TDD** — write tests first
- **Double-quoted docstrings** — `"""` not `'''`; enforced by `ruff format` (formatter always uses `"""` per Black convention)
- **Entitlements** — never inline entitlement logic; always `EntitlementStore.evaluate(...)`
- **Dependencies** — never add/remove without human approval (3 groups: runtime, dev, automation)
- **proto/ is frozen** — `proto/capture.proto` is the authority; rebuild stubs with `uv run python -m tools.build_assets`, never hand-edit

See `AGENTS.md` for complete coding standards.
