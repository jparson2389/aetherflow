# Constraint Inventory

## Scope

Normalized inventory of governing constraints extracted from the canonical
source documents listed below. Intended to support later audit classification.
Each entry carries enough source precision to allow a reviewer to verify the
claim against the original text.

## Source Set

- `docs/PRD.md`
- `docs/PLAN.md`
- `AGENTS.md`
- `docs/verification_standard.md`
- `docs/verify-requirements-pipeline.md`
- `CLAUDE.md`

## Inventory

<!-- prettier-ignore-start -->
| ID     | Source                                 | Source Ref                        | Claim                                                                                                                                 | Classification                         |
|--------|----------------------------------------|-----------------------------------|---------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------|
| CI-001 | `docs/PRD.md`                          | §2 Guidelines                     | Platform scope is Windows-only for v1.                                                                                                | architectural                          |
| CI-002 | `docs/PRD.md`                          | §2 Guidelines                     | Tech stack is C++20 in `host/` and `include/`; Python 3.12 in `src/aetherflow/`.                                                     | architectural                          |
| CI-003 | `docs/PRD.md`                          | §2 Guidelines                     | IPC layer is gRPC control plane plus shared memory data plane; no other inter-process channel is permitted.                            | architectural                          |
| CI-004 | `docs/PRD.md`                          | §2 Guidance                       | TDD is mandatory for all implementation work.                                                                                         | process, testing                       |
| CI-005 | `docs/PRD.md`                          | §2 Guidance                       | Ambiguity defaults to the most restrictive safe behavior.                                                                             | process                                |
| CI-006 | `docs/PRD.md`                          | §2 Guidance                       | Frozen contracts may not change after their freeze point without a documented breaking-change entry and human sign-off.               | process, architectural                 |
| CI-007 | `docs/PRD.md`                          | §2 Guidance                       | File paths named in `docs/PLAN.md` are canonical and must not drift.                                                                 | architectural                          |
| CI-008 | `docs/PRD.md`                          | §2 Guardrails                     | A premium plugin DLL must never load without a valid or GRACE entitlement.                                                            | security                               |
| CI-009 | `docs/PRD.md`                          | §2 Guardrails                     | Unsigned, tampered, expired, or revoked native plugins or protected artifacts must never execute.                                     | security                               |
| CI-010 | `docs/PRD.md`                          | §2 Guardrails                     | C++ code must never appear under `src/`; it belongs only in `host/` and `include/`.                                                  | architectural                          |
| CI-011 | `docs/PRD.md`                          | §2 Guardrails                     | Worker-to-host control traffic must never bypass gRPC.                                                                                | architectural                          |
| CI-012 | `docs/PRD.md`                          | §5.3 Frozen Contracts              | `include/plugin_system.hpp`, `proto/capture.proto`, and `src/aetherflow/core/shared_memory_layout.py` freeze at end of Phase 0.      | architectural, process                 |
| CI-013 | `docs/PRD.md`                          | §5.3 Frozen Contracts              | `src/aetherflow/core/entitlements.py` freezes at end of Phase 4.                                                                     | architectural, process                 |
| CI-014 | `docs/PRD.md`                          | §6.1 Primary Path Latency          | Input-to-output latency: median <= 8 ms, p95 <= 12 ms, jitter p95 <= 2 ms.                                                           | architectural                          |
| CI-015 | `docs/PRD.md`                          | §6.2 Worker Control Plane          | gRPC unary control calls timeout after 750 ms; worker heartbeat interval is 500 ms.                                                   | architectural                          |
| CI-016 | `docs/PRD.md`                          | §6.2 Worker Control Plane          | Worker is marked DEGRADED after 2 missed heartbeats; restart begins after 3; FAILED after 3 restarts within 60 s.                    | architectural                          |
| CI-017 | `docs/PRD.md`                          | §6.4 Capture Stability             | 60 FPS baseline is required on supported hardware; 120 FPS validated path is required for at least one hardware path.                 | architectural                          |
| CI-018 | `docs/PRD.md`                          | §8.1 Trust Baseline                | All shipped native plugins and protected artifacts must use Windows Authenticode, SHA-256, RSA-3072, and publisher-chain validation.  | security                               |
| CI-019 | `docs/PRD.md`                          | §8.2 Premium Load Gating           | When locked, the host must refuse process load, plugin registration, panel/device/service exposure, and remove activation selectors. | security                               |
| CI-020 | `docs/PRD.md`                          | §9.1 Plugin System                 | Default compatibility posture is exact `api_version` match; the host must reject plugins not explicitly marked compatible.            | architectural                          |
| CI-021 | `docs/PRD.md`                          | §9.1 Plugin System                 | Load order is topological by declared dependency; unload order is reverse dependency with quiesce before removal.                     | architectural                          |
| CI-022 | `docs/PRD.md`                          | §9.9 Online Resources              | Install completion must verify entitlement, manifest digest, artifact digest, and signature before activation.                        | security, verification                 |
| CI-023 | `docs/PLAN.md`                         | §Rules                             | Python lives under `src/aetherflow/`; C++ lives only under `host/` and `include/`.                                                   | architectural                          |
| CI-024 | `docs/PLAN.md`                         | §Rules                             | Mandatory validation for completed work is `uv run ruff check .` and `uv run pytest`.                                                | process, testing                       |
| CI-025 | `docs/PLAN.md`                         | §Completion Policy                 | A work item is done only when behavior evidence, test depth, and required artifacts are all present; file presence or stubs alone are insufficient. | process, testing, verification         |
| CI-026 | `docs/PLAN.md`                         | §Atomic Recovery Protocol          | On any validation command exiting non-zero: capture diff, analyze failure, report reason, attempt one fix, revert if fix fails.       | process                                |
| CI-027 | `docs/PLAN.md`                         | §Assumptions — ASM-01              | `proto/` is the authoritative proto source; generated Python stubs land under `src/aetherflow/proto/`.                                | architectural                          |
| CI-028 | `AGENTS.md`                            | §Tech Stack & Conventions          | `uv run` is the only valid Python invocation; `pip` and bare `python` are forbidden.                                                  | process                                |
| CI-029 | `AGENTS.md`                            | §Tech Stack & Conventions          | Generated stubs must go in `src/aetherflow/proto/` and must never be hand-edited or moved.                                           | architectural, process                 |
| CI-030 | `AGENTS.md`                            | §Tech Stack — Ruff                 | Ruff is the authority for Python formatting and linting; always run with `uv run ruff check`.                                         | process                                |
| CI-031 | `AGENTS.md`                            | §Dependencies                      | Dependency groups are fixed; adding, removing, or changing any dependency requires human approval.                                    | dependency                             |
| CI-032 | `AGENTS.md`                            | §Dependencies                      | `protobuf` upper bound `<7.0.0` is intentional; `pyside6==6.9.1` is pinned exactly; neither may change.                              | dependency                             |
| CI-033 | `AGENTS.md`                            | §Architecture Patterns             | In-process embedding of C++ and Python is forbidden; interaction is IPC-only (gRPC control plane, shared memory data plane).         | architectural                          |
| CI-034 | `AGENTS.md`                            | §Architecture — Entitlement SM     | All entitlement resolution must go through `EntitlementStore.evaluate(...)`; reimplementation or inlining is forbidden.               | architectural, security                |
| CI-035 | `AGENTS.md`                            | §Architecture — Entitlement SM     | Entitlement state machine states and transitions may not be modified or extended without human sign-off.                              | security, process                      |
| CI-036 | `AGENTS.md`                            | §Do's and Don'ts                   | New top-level folders must not be created without explicit approval.                                                                  | process                                |
| CI-037 | `AGENTS.md`                            | §Do's and Don'ts                   | `proto/capture.proto` must not be modified without explicit human sign-off.                                                           | architectural, process                 |
| CI-038 | `AGENTS.md`                            | §Do's and Don'ts                   | All Python functions, methods, and classes must have full type hints and Google-format docstrings.                                    | process                                |
| CI-039 | `AGENTS.md`                            | §Testing & Quality                 | TDD is mandatory: test files must be implemented before feature code.                                                                 | testing                                |
| CI-040 | `AGENTS.md`                            | §Testing & Quality                 | Lint and test must both pass before build loop or merge succeeds.                                                                     | process, testing                       |
| CI-041 | `AGENTS.md`                            | §Common Pitfalls                   | Every used symbol must be imported in its file; do not assume cross-file scope from a code-generation payload.                        | process                                |
| CI-042 | `AGENTS.md`                            | §Common Pitfalls                   | All tests must be hermetic: mock processes and use `tmp_path`; real FS or cert state must not be required.                            | testing                                |
| CI-043 | `docs/verification_standard.md`        | §Evidence Requirements             | Every non-retired plan item must define 1-3 acceptance criteria, at least one behavioral proof, and reviewer sign-off before `verified`. | verification                           |
| CI-044 | `docs/verification_standard.md`        | §What Does Not Count As Proof      | File existence, placeholder scans, import success, thin tests, and "no exceptions thrown" are not acceptable proof of completion.     | verification, testing                  |
| CI-045 | `docs/verification_standard.md`        | §Feature-Class Rules               | `boundary` items require contract proof and negative-path validation.                                                                 | verification, testing                  |
| CI-046 | `docs/verification_standard.md`        | §Failure Conditions                | An item may not be promoted to `verified` if acceptance criteria are missing, no behavioral proof exists, or sign-off is absent.      | verification, process                  |
| CI-047 | `docs/verify-requirements-pipeline.md` | §Verification Authority            | The singular canonical verification command is `uv run python -m tools.verify_requirements`; other tools are not equivalent authorities. | verification                           |
| CI-048 | `docs/verify-requirements-pipeline.md` | §Heuristics                        | Status heuristics and placeholder classifications are advisory only; they do not establish functional completion or performance verification. | verification                           |
| CI-049 | `CLAUDE.md`                            | §Claude-Specific Expectations      | Make the smallest safe change that satisfies the task; do not restate success without running verification.                           | process, verification                  |
| CI-050 | `CLAUDE.md`                            | §Environment Notes                 | Prefer `uv run python -m tools.*` entry points where available.                                                                       | process                                |
| CI-051 | `docs/governance/artifact-storage-policy.md` | §Tier 2 — Generated runtime | `logs/verification/*.json` and `status_snapshot.json` are generated runtime artifacts; they must never be git-tracked.              | process, verification                |
| CI-052 | `docs/governance/artifact-storage-policy.md` | §Enforcement              | `.gitignore` must include `logs/verification/*.json` exactly once; `!logs/verification/` negation exceptions are forbidden.           | process                                |
| CI-053 | `docs/governance/artifact-storage-policy.md` | §Enforcement              | CI must run `uv run python -m tools.verify_requirements` before pytest so generated verification JSON exists without git tracking.   | process, verification                |
| CI-054 | `docs/governance/artifact-storage-policy.md` | §Tier 1 — Canonical tracked | Governance docs and ledger YAML under `docs/governance/` are canonical tracked artifacts.                                            | process                                |
<!-- prettier-ignore-end -->

## Classification Key

Classifications are drawn from: `architectural`, `process`, `testing`,
`dependency`, `security`, `verification`. An entry may carry more than one
classification when the constraint spans multiple concerns.
