## Relevant Files

- `docs/evidence/AF-01-02.md` — Evidence pack requiring AC criterion text correction, developer alert correction, and removal of undeclared test file citation. Addresses H-1, H-2, H-3.
- `logs/verification/AF-01-02.json` — Verification JSON to regenerate after evidence and test suite corrections. Addresses H-1, H-2, H-3, M-1.
- `tests/integration/test_plugin_catalog_locking.py` — Declared integration test file; must receive a new test for the `shell.mark_failed()` RuntimeState.FAILED path. Addresses M-1, CG-3.
- `tests/ui/test_shell_router.py` — Exists and contains relevant behavior tests; work item scope decision required (declare as target or remove evidence citation). Addresses H-2, DA-1.
- `docs/PLAN.md` — If `tests/ui/test_shell_router.py` is added to scope, target file and validation command declarations must be updated here. Addresses H-2, DA-1.
- `src/aetherflow/ui/shell.py` — Contains `mark_failed()` method under test. No changes required, read for test authoring context.

### Notes

- Authoritative work item definition is in `docs/PLAN.md` under `AF-01-02`.
- Failed requirement IDs addressed by this file: **EVD-1 (H-1), EVD-2 (H-2), EVD-3 (H-3), CG-3 (M-1)**.
- Derived auditor finding addressed: **DA-1**.
- Validation command for this work item: `uv run pytest tests/unit/test_entitlements.py tests/integration/test_plugin_catalog_locking.py tests/ui/test_status_hud.py`
- If `tests/ui/test_shell_router.py` is added to PLAN scope, update the validation command in PLAN.md to: `uv run pytest tests/unit/test_entitlements.py tests/integration/test_plugin_catalog_locking.py tests/ui/test_status_hud.py tests/ui/test_shell_router.py`
- Run linting after any evidence or source changes: `uv run ruff check`
- All tests must pass at exit code 0 before regenerating evidence.

## Instructions for Completing Tasks

**IMPORTANT:** As each task is completed, update this file by changing `- [ ]` to `- [x]`.

## Tasks

- [x] 0.0 Create feature branch
  - [x] 0.1 Create and checkout a new branch for this remediation work (e.g., `fix/af-01-02-evidence-remediation`)

- [x] 1.0 Fix evidence AC criterion text mismatch (H-1 / EVD-1)
  - [x] 1.1 Open `docs/evidence/AF-01-02.md` and locate the Acceptance Criteria section.
  - [x] 1.2 Replace the AC1 criterion text with the exact text from `docs/PLAN.md`: `AC1: LOCKED state blocks plugin activation.`
  - [x] 1.3 Verify AC2 and AC3 criterion text also exactly match PLAN AC2 and AC3 respectively: `AC2: Status HUD reflects degraded state.` and `AC3: Shell survives plugin failure.`

- [x] 2.0 Fix Developer-Alert-Message in evidence artifact (H-3 / EVD-3)
  - [x] 2.1 Open `docs/evidence/AF-01-02.md` and locate the `Developer Alert` field in the header metadata.
  - [x] 2.2 Replace `New feature added, check for functionality` with the PLAN-specified message: `Entitlement state degraded — check plugin trust and license status`

- [x] 3.0 Resolve undeclared test file citation in evidence (H-2 / EVD-2 / DA-1)
  - [x] 3.1 Decision point — choose ONE of the following paths:
    - **Path A (Expand scope):** Add `tests/ui/test_shell_router.py` as a declared target file in `docs/PLAN.md` under `AF-01-02`, and add it to the PLAN validation command. Update evidence proof matrix to retain the citation and annotate that it is now declared.
    - **Path B (Restrict scope):** Remove all citations of `tests/ui/test_shell_router.py` from `docs/evidence/AF-01-02.md`. Ensure AC1 proof in the evidence matrix only cites declared files: `tests/integration/test_plugin_catalog_locking.py` and `tests/unit/test_entitlements.py`.
  - [x] 3.2 Apply the chosen path consistently across `docs/evidence/AF-01-02.md` and (if Path A) `docs/PLAN.md`.

- [x] 4.0 Add mark_failed() shell survival test to close CG-3 (M-1 / CG-3)
  - [x] 4.1 Open `tests/integration/test_plugin_catalog_locking.py` (or `tests/ui/test_shell_router.py` if added to scope under Task 3 Path A).
  - [x] 4.2 Add a new test: `test_shell_survives_plugin_mark_failed`. The test must:
    - Instantiate `ShellModel` with a `RouterModel` containing at least one registered route.
    - Call `shell.mark_failed('some.plugin', reason='unrecoverable-fault')`.
    - Assert `shell.runtime_state is RuntimeState.FAILED`.
    - Assert the shell model is still accessible (e.g., `shell.active_panel_id()` does not raise, `shell.notices` is readable).
    - Assert `'some.plugin' in shell.degraded_plugins`.
    - Assert a notice was added with severity `'error'`.
  - [x] 4.3 Run `uv run pytest <test-file> -v` and confirm the new test passes.

- [x] 5.0 Run full validation command and confirm clean pass
  - [x] 5.1 Run: `uv run pytest tests/unit/test_entitlements.py tests/integration/test_plugin_catalog_locking.py tests/ui/test_status_hud.py -v` (add test_shell_router.py if Path A was chosen in Task 3).
  - [x] 5.2 Confirm exit code 0 and all tests pass.
  - [x] 5.3 Run: `uv run ruff check` and confirm no lint errors.

- [x] 6.0 Regenerate evidence artifacts
  - [x] 6.1 Update `docs/evidence/AF-01-02.md` proof matrix to reflect all corrections from Tasks 1–4.
  - [x] 6.2 Update `logs/verification/AF-01-02.json` to reflect the corrected validation results, including the new test for mark_failed() under `validation_results` and `requirement_links`.
  - [x] 6.3 Confirm `logs/verification/AF-01-02.json` is parseable and `requirement_links.acceptance_criteria` covers all three ACs.
