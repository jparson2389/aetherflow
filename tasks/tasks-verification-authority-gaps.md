## Relevant Files

- `tools/generate_verification_report.py` - Non-authoritative wrapper; needs docstring correction.
- `tools/audit_plan_completion.py` - Advisory-only heuristic auditor; needs module docstring.
- `tools/verify_requirements.py` - Canonical regrade entry point; needs module docstring asserting authority. Also needs `--acknowledge` CLI flag wired to `PendingAppCheckStore.acknowledge()`.
- `src/aetherflow/core/verification_report.py` - Canonical evaluator; gap-collection functions need category-tagged gap strings.
- `src/aetherflow/core/developer_app_checks.py` - `acknowledge()` is implemented but not reachable from any CLI.
- `docs/verification_standard.md` - Needs a "How to acknowledge an alert" section.
- `docs/PLAN.md` - All active AF items must carry the full required metadata set.
- `tests/contracts/test_verification_reporting.py` - Existing test file; extend with exhaustive metadata and tool-authority tests.
- `tests/contracts/test_tool_authority.py` - New file for tool-authority contract tests.

### Notes

- Run tests with `uv run pytest tests/contracts/` — not `npx jest`.
- `audit_plan_completion.py` currently suppresses all docstring warnings via `# ruff: noqa: D101,D102,D103` on line 1. A module-level docstring (`"""..."""`) before any imports is still emitted even with those noqa codes and does not need a noqa exemption — add it above the noqa comment.
- Gap category tags must match the six names defined in `PLAN.md` exactly: `metadata-gap`, `ac-coverage-gap`, `failure-coverage-gap`, `validation-gap`, `review/sign-off-gap`, `performance-proof-gap`.
- Do not change existing test assertions until after the gap-string format is updated, to avoid test breakage during transition.
- `verify_requirements.py` has no module docstring at all (starts directly with `from __future__`). Add one.

## Instructions for Completing Tasks

**IMPORTANT:** As you complete each task, you must check it off in this markdown file by changing `- [ ]` to `- [x]`. This helps track progress and ensures you don't skip any steps.

Update the file after completing each sub-task, not just after completing an entire parent task.

## Tasks

- [x] 0.0 Create feature branch
  - [x] 0.1 Create and checkout a new branch for this feature (e.g., `git checkout -b feature/verification-authority-gaps`)

- [x] 1.0 Mark non-authoritative tools as non-authoritative in code
  - [x] 1.1 Replace the module docstring in `tools/generate_verification_report.py:1` — change `"""Generate evidence-based verification artifacts for plan items."""` to one that explicitly states this is a non-authoritative compatibility wrapper around `src/aetherflow/core/verification_report.py` and must not be treated as a second verification authority.
  - [x] 1.2 Add a module docstring to `tools/audit_plan_completion.py` (insert above the `# ruff: noqa:` line on line 1) stating that this tool is advisory-only and heuristic, that its output must never be used to claim or promote a `verified` status, and that the canonical regrade command is `uv run python -m tools.verify_requirements`.
  - [x] 1.3 Add a module docstring to `tools/verify_requirements.py` (insert before `from __future__`) stating that this is the canonical repo regrade entry point, that it is the only tool authorized to write `docs/requirements-report.md` and `logs/verification/<item-id>.json`, and that wrapper scripts must not be treated as equivalent authorities.

- [x] 2.0 Add missing test: non-authoritative tools cannot claim or promote `verified`
  - [x] 2.1 Create `tests/contracts/test_tool_authority.py` with the required imports (`subprocess`, `Path`, `PROJECT_ROOT`).
  - [x] 2.2 Add `test_audit_plan_completion_does_not_write_verification_outputs()` — run `audit_plan_completion.py` against the repo, then assert that `docs/requirements-report.md` was not modified (check mtime before/after or that the file does not appear in the tool's stdout) and that no files were written under `logs/verification/`.
  - [x] 2.3 Add `test_generate_verification_report_is_a_pure_wrapper()` — run `generate_verification_report.py` and then run `verify_requirements.py`; assert that both produce identical status values for each AF item in `logs/verification/`. This confirms the wrapper does not independently compute or override status.
  - [x] 2.4 Add `test_audit_plan_completion_stdout_contains_no_verified_claim()` — run `audit_plan_completion.py` and assert its stdout/output does not contain the string `"verified"` as a status assertion (it may mention the word, but must not emit a structured verified status for any item).

- [x] 3.0 Exhaustively validate all active AF items have required metadata
  - [x] 3.1 Read `tests/contracts/test_verification_reporting.py` to understand the existing `test_parser_reads_canonical_metadata_from_plan()` at line 44 — it currently spot-checks only AF-01-02, AF-02-02, and AF-04-02.
  - [x] 3.2 Add `test_all_active_af_items_have_complete_required_metadata()` to `tests/contracts/test_verification_reporting.py`. This test must: (a) call `parse_plan_items()` on `docs/PLAN.md`, (b) filter to items where `lifecycle_state` is not `retired`, (c) for each active item assert that `feature_class`, `entry_point`, `required_proofs`, `failure_modes`, and `acceptance_criteria` are all non-empty, and (d) for items where `performance_claim` is True, also assert that `performance_threshold`, `performance_evidence_type`, and `performance_evidence_location` are non-empty.
  - [x] 3.3 Run `uv run pytest tests/contracts/test_verification_reporting.py::test_all_active_af_items_have_complete_required_metadata` and fix any active AF items in `docs/PLAN.md` that fail the assertion by filling in the missing metadata fields.

- [x] 4.0 Add formal gap-category tags to closure matrix report output
  - [x] 4.1 Read `src/aetherflow/core/verification_report.py` functions `_collect_metadata_gaps()` (line 688), `_collect_evidence_gaps()` (line 722), and `evaluate_plan_item()` (line 517) to understand where each gap string is produced.
  - [x] 4.2 Prefix each gap string at its source with its PLAN.md category tag in brackets. Mapping: all strings from `_collect_metadata_gaps()` → `[metadata-gap]`; AC-coverage strings from `_collect_evidence_gaps()` → `[ac-coverage-gap]`; failure-coverage strings → `[failure-coverage-gap]`; performance-artifact strings → `[performance-proof-gap]`; validation-failure strings (produced in `evaluate_plan_item()`) → `[validation-gap]`; reviewer sign-off strings → `[review/sign-off-gap]`; entry-point strings → `[ac-coverage-gap]` (entry point not exercised blocks AC proof).
  - [x] 4.3 Update `write_results()` (line 941) — the gap line is currently `f'- Gaps: {"; ".join(result.gaps)}'`. No change to structure needed if gap strings already carry category tags; verify the output is readable.
  - [x] 4.4 Update any existing test assertions in `tests/contracts/test_verification_reporting.py` that assert on exact gap string content — add the expected category prefix to each asserted string.
  - [x] 4.5 Run `uv run pytest tests/contracts/` and confirm all tests pass.

- [x] 5.0 Document app-check acknowledgement workflow for users
  - [x] 5.1 Add an `--acknowledge <item-id>` argument to `tools/verify_requirements.py`'s `build_argument_parser()` function. When provided, instantiate `PendingAppCheckStore` with the standard paths and call `store.acknowledge(args.acknowledge)`, then exit without running a full regrade.
  - [x] 5.2 Wire the new argument in `verify_requirements.py`'s `main()` function: check for `args.acknowledge` before the regrade path; if set, call acknowledge and return 0.
  - [x] 5.3 Extend `docs/verification_standard.md` with a new "## Acknowledging an Alert" section after the existing "Developer App-Check Alerts" section. The section must describe: (a) what triggers an alert (item transitions to `verified` with `App-Testable: true`), (b) the command to list pending alerts (`uv run python -m tools.verify_requirements` — alerts appear in the startup notice), (c) the command to acknowledge (`uv run python -m tools.verify_requirements --acknowledge <item-id>`), and (d) the effect (alert removed from `logs/verification/pending_app_checks.json`).
  - [x] 5.4 Add `test_acknowledge_flag_removes_alert_from_pending()` to `tests/contracts/test_tool_authority.py` — seed a `pending_app_checks.json` with a known item ID, run `verify_requirements --acknowledge <item-id>` via subprocess, then assert the alert is no longer in the pending file.
