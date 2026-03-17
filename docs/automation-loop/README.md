# Automation Loop Onboarding

## Purpose

This document explains the current automation loop in Aetherflow from startup
through one execution pass, including the supporting files, runtime invariants,
state artifacts, and the `tools/` functions that matter to the live path.

The short version is:

- `start-loop2.ps1` bootstraps the local model router and validates alias
  inventory against repo config.
- `tools/plan_exec.py` is the real executor. It selects one PLAN item, tries to
  implement it, runs build and quality checks, runs the physical validation
  gate, asks the PM to semantically verify the result, writes state and logs,
  then exits.
- There is no in-repo forever runner that repeatedly invokes `plan_exec`.
  Repetition is operator-driven or handled by an external wrapper not present in
  this repository.

## What Defines The Loop

These files are the control plane for the loop:

- `start-loop2.ps1`
  Bootstrap script for `llama-server`. It also runs `uv sync --group dev
  --group automation`, validates the `/health` endpoint, and confirms that the
  expected model aliases exist and match the preset.
- `scripts/start-llama-server.ps1`
  Byte-identical duplicate of `start-loop2.ps1`. Both files currently hash to
  the same SHA-256 value.
- `agent_manifest.json`
  Runtime manifest. Defines `base_url`, `grammar_capable`, required aliases,
  optional aliases, `role_to_alias`, `role_to_context`, and `stage_to_alias`.
- `tools/models.ini`
  Source-of-truth alias preset consumed by `llama-server` router mode.
- `docs/PLAN.md`
  The executor's task ledger. `plan_exec` parses phases, checklist items, role,
  target files, validation commands, PRD refs, and behavior text from here.
- `docs/PRD.md`
  The executor extracts selected "hard requirement" sections and includes them
  in LLM prompts.
- `tools/plan_exec.py`
  Single-pass orchestration engine for one PLAN item.
- `.cursor/workflows/build-assets.ps1`
  Post-write asset build step.
- `.cursor/workflows/check-quality.ps1`
  Post-build quality gate wrapper.
- `state/plan_state.json`
  Persisted execution state and history.
- `logs/`
  Prompt dumps, invalid LLM responses, execution logs, reconciliation audit,
  and post-run reports.

## Alias And Role Routing

The routing model is split across `agent_manifest.json` and `tools/models.ini`.

Manifest stage routing:

- `pm_next` -> `pm`
- `pm_verify` -> `pm`
- `quick_fix` -> `quick-fix`
- `manual_research` -> `researcher`

Manifest role routing:

- `core-runtime` -> `architect`
- `trust-security` -> `trust-security`
- `platform-entitlements` -> `runtime-services`
- `native-io-capture` -> `architect`
- `runtime-services` -> `runtime-services`
- `ui-shell` -> `ui-ux`

Operational meaning:

- `pm` is the planner and semantic verifier.
- `architect`, `trust-security`, `runtime-services`, and `ui-ux` are the
  implementation aliases selected from the PLAN item's `**Role:**` field.
- `quick-fix` is only used after the scoped quality gate fails.
- `researcher` is optional and is not used by the main executor path.

Important router detail:

- `start-loop2.ps1` launches `llama-server` with `--models-max 1` and
  `--parallel 1`.
- That means alias inventory is exposed as if multiple models exist, but the
  router only keeps one loaded at a time.

## The Real Runtime Model

The current loop is better understood as two layers:

```text
operator or external wrapper
    -> start-loop2.ps1
        -> local llama-server router
    -> one invocation of tools/plan_exec.py
        -> reconcile repo vs state
        -> choose one work item
        -> implement
        -> build
        -> quality gate
        -> validation gate
        -> PM semantic verify
        -> write state/logs
        -> exit
```

The repo does not contain a script that continuously re-runs `plan_exec.py`
until the PLAN is complete.

## End-To-End Flow A-Z

### A. Bootstrap The Router

`start-loop2.ps1` performs these steps:

1. Read `agent_manifest.json`.
2. Resolve the router root URL from `base_url`.
3. Parse alias expectations from `tools/models.ini`.
4. Verify the hardcoded `llama-server.exe` exists at
   `C:\Users\Dada\AI_Tools\llama.cpp\build\bin\Release\llama-server.exe`.
5. Run `uv sync --group dev --group automation`.
6. Check whether the configured port is already in use.
7. If an existing `llama-server` is on that port, validate health and alias
   inventory against the repo preset.
8. If the existing process does not match the preset, kill it and restart.
9. Start `llama-server` in models-preset router mode.
10. Poll `/health`.
11. Poll `/models` or `/v1/models`.
12. Fail fast if required aliases are missing or if preset settings drift.

Key PowerShell helpers inside `start-loop2.ps1`:

- `Get-ManifestConfig`
- `Get-PresetAliasConfig`
- `Get-AvailableModels`
- `Wait-ForServerHealth`
- `Wait-ForAliasInventory`
- `Get-MismatchedAliases`
- `Write-AliasSummary`

### B. Invoke The Executor

The actual loop body lives in `tools/plan_exec.py`.

The script supports these executor-side CLI flags:

- `--plan`, default `docs/PLAN.md`
- `--prd`, default `docs/PRD.md`
- `--manifest`, default `agent_manifest.json`
- `--max-doc-chars`, default `32000`
- `--state-only`, reconcile state and exit without LLM execution

### C. Load Documents And Manifest

`plan_exec.main()` reads:

- manifest from `agent_manifest.json`
- PLAN text from `docs/PLAN.md`
- PRD text from `docs/PRD.md` if it exists

It then computes:

- `grammar_capable` from the manifest or a local-backend URL heuristic
- `plan_summary` via `extract_plan_phase_summary()`
- `prd_summary` via `extract_prd_hard_requirements()`

`extract_prd_hard_requirements()` only keeps PRD sections whose `##` headers
contain:

- `architectural`
- `plugin system`
- `capture system`

If none match, it falls back to the whole PRD excerpt.

### D. Parse PLAN.md Into Structured Work Items

`extract_phase_work_items()` is one of the most important functions in the
system.

It parses:

- phase headers like `## Phase 0 - ...`
- checklist items like `- [ ] ...` or `- [x] ...`
- quoted instruction lines starting with `>`
- the `**Role:**` field

Each parsed item becomes a `PlanWorkItem` with:

- `id`
- `phase`
- `title`
- `status`
- `instructions`
- `role`

The item `id` is derived by `work_item_id()`.

Important behavior:

- If the title contains an explicit token like `AF-00-04`, the ID becomes a
  stable slug such as `af_00_04`.
- This prevents plan reformatting from invalidating saved state.

### E. Load And Normalize Persisted State

`load_or_initialize_plan_state()` merges PLAN-derived items with
`state/plan_state.json`.

What it preserves:

- prior item status
- notes
- missing reasons
- evidence
- history

What it also does:

- accepts legacy IDs and maps them to the stable token-derived ID
- replays latest history status back onto the current item list
- writes the normalized state back to disk immediately

State items use these statuses in practice:

- `missing`
- `in_progress`
- `blocked`
- `partial`
- `done`
- `verified`

Only `done` and `verified` count as complete for phase progression.

### F. Reconcile Before Calling Any Model

`reconcile_state_with_repo()` runs before PM selection.

This is a critical behavior:

- It looks only at the earliest incomplete phase.
- For each incomplete item in that phase, it runs the physical validation gate
  against the repo as it currently exists.
- If the repo already satisfies the item's target files and validation command,
  the item is promoted to `verified` without any new model call.

Side effects of successful reconciliation:

- item status is updated to `verified`
- history entry is appended
- `logs/plan_reconciliation_audit.md` receives a Markdown audit entry
- `state/plan_state.json` is re-saved

This means the executor can "skip work" when earlier phases were already
implemented outside the loop.

### G. Stop Early If No Open Work Remains

After reconciliation:

- if `--state-only` was passed, the script exits `0`
- if no open items remain, the script exits `0`
- otherwise it selects the earliest incomplete phase and all incomplete items in
  that phase

### H. PM Chooses Exactly One Work Item

`pm_next` is the first LLM stage.

Prompt inputs:

- earliest incomplete phase
- open items in that phase
- exact item IDs and titles
- each item's instruction block from `PLAN.md`
- PRD excerpt
- PLAN excerpt

Expected JSON contract:

- phase
- one `work_items` entry
- that entry must include `id`, `title`, `acceptance`, and `notes`

Selection hardening:

- `PMResponse` must validate
- exactly one work item must be returned
- returned phase must match the selected phase
- returned `id` must be one of the open IDs
- returned title must exactly match the PLAN item title for that ID

Fallback behavior:

- if the PM response is invalid or mismatched, `plan_exec` falls back to the
  first open item in the phase
- fallback is logged with `[pm_next] invalid_selection=... fallback=true`

This fallback keeps the loop moving even if planning output drifts.

### I. Resolve The Implementation Alias

Once an item is final, `plan_exec` looks up its PLAN role.

It then resolves:

- runtime alias with `resolve_role_alias()`
- persona text with `resolve_role_context()`
- final implementation system prompt with
  `build_role_scoped_impl_system()`

Important prompt composition detail:

- `IMPL_SYSTEM` already includes the JSON-write contract and the full contents
  of `AGENTS.md`
- `build_role_scoped_impl_system()` prepends the manifest's role-specific
  persona text to that base system prompt

### J. Build The Implementation Prompt

The implementation prompt includes:

- selected item ID
- exact title
- raw PLAN requirement block
- filtered acceptance criteria
- PRD excerpt
- hard constraints like "do not implement other PLAN items yet"

Acceptance criteria are post-processed by `filter_acceptance_criteria()` so the
executor tries to keep the implementation scoped to the chosen title instead of
phase-wide goals.

### K. Track Context Budget

The loop uses `ContextMonitor.track_usage()` and `count_tokens()` before the
implementation call.

Actual behavior:

- it estimates tokens with a whitespace counter, not a real tokenizer
- if usage is high, it logs a warning
- if usage is near the fallback threshold, it clips `prd_summary` and
  `plan_summary`

This subsystem is advisory. It does not swap models automatically.

### L. Call The Implementation Model

`call_json_with_retry()` wraps the actual LLM call path.

Core mechanics:

- `call()` sends an OpenAI-compatible chat request
- if `grammar_capable` is true and a grammar is supplied, the executor sends
  `extra_body={"grammar": ...}` instead of `response_format`
- if the first response cannot be parsed as JSON, a repair prompt is sent
- if both responses fail, the raw responses are dumped under `logs/`

Per-stage prompt logging:

- `logs/prompt_system_<stage>.txt`
- `logs/prompt_user_<stage>.txt`
- `logs/prompt_repair_user_<stage>.txt` when a repair pass is needed

Invalid-response logging:

- `logs/plan_exec_<stage>_first_<timestamp>.txt`
- `logs/plan_exec_<stage>_retry_<timestamp>.txt`

### M. Parse And Repair The Writes Payload

Implementation output is expected to match the `writes` schema:

- top-level `writes` array
- top-level `notes` string
- each write entry has `path` and `content`

Validation path:

1. `call_json_with_retry()` parses raw JSON with `safe_json_from_model()`.
2. `validate_writes_payload()` validates shape and path safety.
3. `WritesPayload` and `WriteEntry` from `validation_gate.py` normalize Python
   docstring quotes.

Auto-repair path:

- `coerce_impl_payload()` can do one safe repair without consuming a retry
  attempt.
- It can wrap a single top-level `path` and `content`, rename `write` to
  `writes`, wrap a dict into a one-item list, and inject missing `notes`.

Classification:

- schema-like failures are classified as `writes_schema_fail`
- path/location failures are classified as `writes_path_fail`

### N. Enforce Write Safety

`tools/apply_writes.py` is the write firewall.

Allowed write prefixes:

- `src/aetherflow/`
- `include/`
- `host/`
- `.cursor/`
- `.github/`
- `proto/`
- `assets/`
- `tests/`
- `docs/`
- `state/`

Allowed root files:

- `pyproject.toml`
- `README.md`

Denied paths:

- `PLAN.md`
- `PRD.md`
- `docs/plan.md`
- `docs/prd.md`

Also rejected:

- absolute paths
- traversal paths
- obvious placeholder paths like `replace/with/real/path.py`

Important consequence:

- the executor cannot directly rewrite `docs/PRD.md`
- the executor cannot directly rewrite `docs/PLAN.md`
- the executor also cannot write `.agents/...` because `.agents/` is not in the
  allowlist

This matters because some PLAN items list files that the executor itself cannot
write. Those items can still become `verified` through reconciliation if the
repo already satisfies them, but the loop will not generate those files through
its normal write path.

### O. Snapshot Existing Files Before Overwriting

`capture_existing_file_snapshots()` records:

- repository-relative path
- SHA-256 of the old file bytes
- truncated pre-write file content

These snapshots feed retry prompts so later attempts can see both the current
artifact and the pre-write state.

### P. Apply Writes And Auto-Format

`apply_writes_relpaths()` calls `apply_writes()`, which writes the full file
contents to disk.

After a successful write pass:

- changed files are converted to repo-relative paths
- `uv run ruff format <changed files>` is invoked

Hard stop:

- if the model returns zero writes, the executor treats that as failure and
  retries or blocks the task

### Q. Build Assets

`run_ps('.cursor/workflows/build-assets.ps1')` always runs after successful
writes.

That script currently does two things:

- compile every `.proto` file in `proto/` into `src/aetherflow/proto/`
- convert every `assets/ui/*.ui` file into `src/aetherflow/ui_<name>.py`

If asset build fails:

- the executor builds a retry prompt with clipped build output
- after final failure it marks the item `blocked`

### R. Run The Quality Gate

The next step is:

- `.cursor/workflows/check-quality.ps1`

The executor scopes it with `quality_scope_args(changed)` when possible.

Actual workflow behavior:

- if there are Python files in scope, it runs scoped `ruff check --fix` and
  scoped `ruff format`
- it still runs full `pytest`, not a scoped test subset
- if there are no Python files in scope, it skips lint, format, and tests

If quality fails:

- the executor constructs a focused retry prompt
- it calls the `quick-fix` alias
- it validates and applies the quick-fix writes
- it reruns the quality gate once more
- if quality still fails on the last retry, the task is marked `blocked`

### S. Run The Physical Validation Gate

`run_validation_gate()` is the non-LLM gate.

Layer 1:

- `check_filesystem_existence()`
- confirms every `**Target File:**` from the PLAN instruction block exists
- if there are no target files, any changed file satisfies the gate

Layer 2:

- `extract_validation_command()`
- `run_validation_command()`
- executes the PLAN-declared validation command inside the repo root

Validation command allowlist:

- `uv run pytest ...`
- `uv run ruff check ...`
- PowerShell with exactly `-ExecutionPolicy Bypass -File <repo-local-script>`

Explicitly rejected:

- shell chaining
- redirection
- command substitution
- PowerShell scripts outside the repo root

Structured diagnostics captured by the gate include:

- command
- return code
- stdout excerpt
- stderr excerpt
- target files
- failing test
- assertion excerpt
- exception excerpt

If the physical gate fails:

- the executor retries with a prompt that includes current artifact context
- after the final retry it marks the item `blocked`

### T. Run PM Semantic Verification

If and only if the physical gate passes, the loop asks the PM to do semantic
review with the `pm_verify` stage.

Inputs to PM verify:

- chosen item ID and title
- acceptance criteria
- changed files
- serialized gate layers
- PRD summary
- PLAN summary

The PM is told:

- filesystem and validation command already passed
- only semantic completeness should be judged now
- only the listed acceptance criteria matter

Verdict parsing:

- `PMVerdict` expects only `status`, `missing`, and `notes`
- if parsing fails, the executor strips unknown keys and retries validation
- if the PM still does not pass the item after the last retry, the item becomes
  `partial`

This is the only stage that can produce `partial`.

### U. Persist Final Outcome

On full success:

- item status becomes `verified`
- notes are stored from PM verify
- evidence becomes the changed file list
- history entry is appended
- `state/plan_state.json` is saved
- the process exits `0`

On final implementation, build, quality, or physical-gate failure:

- item status becomes `blocked`
- missing reasons and evidence are stored
- state is saved
- the process exits `1`

On final PM semantic failure:

- item status becomes `partial`
- missing reasons are stored
- state is saved
- the process exits `1`

### V. Generate Human-Facing Reports

The reporting loop is separate from execution, but it is part of day-to-day
operation.

`.cursor/workflows/plan-exec-report.ps1`:

- reads the latest `logs/plan_execution_*.log`
- extracts `[state]` lines, execution summaries, warnings, and errors
- snapshots `git status --porcelain`
- writes `logs/plan_exec_report_<timestamp>.md`

This script is not called by `plan_exec.py`, but it is the repo's main post-run
inspection tool.

### W. Repeat Externally

Because `plan_exec.py` handles only one item per invocation, the outer loop is:

1. make sure the router is running
2. invoke `plan_exec.py`
3. inspect `state/` and `logs/`
4. optionally generate a run report
5. invoke `plan_exec.py` again

That repeated invocation mechanism is not implemented inside this repository.

## Key Runtime Artifacts

### State

`state/plan_state.json` is the executor's checkpoint file.

It stores:

- normalized item list
- per-item status, notes, missing reasons, and evidence
- execution history
- `updated_at`

Important nuance:

- history is appended on reconciliation promotions and final verified success
- the current code does not append history for every `blocked` or `partial`
  result

### Logs

Main log outputs:

- `logs/plan_execution_<date>.log`
- `logs/plan_reconciliation_audit.md`
- `logs/plan_exec_report_<timestamp>.md`
- prompt dumps and invalid JSON response dumps

### Evidence Pipeline

The repo also has a separate evidence/reporting path:

- `.cursor/workflows/verify-requirements.ps1`
- `tools/generate_verification_report.py`
- `logs/verification/*.json`
- `logs/verification/status_snapshot.json`
- `docs/requirements-report.md`

This is associated with plan/evidence reporting, but it is not part of the live
`start-loop2.ps1` -> `tools/plan_exec.py` execution path.

## Key Functions In Loop-Utilized `tools/` Modules

### `tools/plan_exec.py`

Primary entrypoint:

- `main()`

State and PLAN parsing:

- `extract_work_item_token()`
- `work_item_id()`
- `extract_phase_work_items()`
- `load_or_initialize_plan_state()`
- `save_plan_state()`
- `next_open_work_items()`
- `update_state_item()`
- `append_history()`

Routing and prompt setup:

- `resolve_role_alias()`
- `resolve_role_context()`
- `build_role_scoped_impl_system()`
- `extract_plan_phase_summary()`
- `extract_prd_hard_requirements()`
- `filter_acceptance_criteria()`

LLM call stack:

- `_build_messages()`
- `_build_extra_body()`
- `call()`
- `_write_failed_response()`
- `call_json_with_retry()`

Retry and recovery helpers:

- `read_file_retry_context()`
- `build_retry_prompt()`
- `coerce_impl_payload()`
- `classify_validate_error()`
- `_gather_gate_evidence()`

Repo execution helpers:

- `reconcile_state_with_repo()`
- `append_reconciliation_audit_entries()`
- `format_reconciliation_audit_entry()`
- `run_ps()`
- `apply_writes_relpaths()`
- `quality_scope_args()`

### `tools/validation_gate.py`

Writes payload normalization:

- `normalize_docstring_quotes()`
- `WriteEntry.normalize_py_docstrings()`

PLAN instruction parsing:

- `extract_target_files()`
- `extract_validation_command()`

Physical gate execution:

- `check_filesystem_existence()`
- `_parse_validation_command()`
- `run_validation_command()`
- `run_validation_gate()`

Report models:

- `WritesPayload`
- `GateResult`
- `ValidationReport`

### `tools/apply_writes.py`

Write safety and application:

- `is_write_path_allowed()`
- `validate_writes_payload()`
- `_safe_path()`
- `capture_existing_file_snapshots()`
- `apply_writes()`

### `tools/json_utils.py`

Schema contracts:

- `WRITES_RESPONSE_FORMAT`
- `PM_NEXT_RESPONSE_FORMAT`
- `PM_VERIFY_RESPONSE_FORMAT`

JSON extraction:

- `_extract_fenced_json()`
- `_extract_first_json_object()`
- `parse_json_object()`
- `safe_json_from_model()`

### `tools/prompts.py`

Prompt constants:

- `SYSTEM_JSON_WRITES`
- `IMPL_SYSTEM`
- `SYSTEM_PM_NEXT`
- `SYSTEM_PM_VERIFY`

### `tools/context_utils.py`

Prompt budget helpers:

- `count_tokens()`
- `ContextMonitor.track_usage()`
- `ContextMonitor.get_model_stats()`

Only `count_tokens()` and `track_usage()` are on the live executor path.

### `tools/shell_utils.py`

Shell normalization:

- `resolve_powershell_executable()`
- `normalize_powershell_command()`

### `tools/gbnf_grammars.py`

Grammar definitions:

- `GBNF_WRITES`
- `GBNF_PM_NEXT`
- `GBNF_PM_VERIFY`
- `is_local_backend()`

## Important Invariants And Gotchas

- The loop is single-pass, not a daemon.
- Execution is phase-ordered. Only the earliest incomplete phase is eligible.
- The PM does not choose the implementation alias. PLAN role and manifest
  routing do.
- Reconciliation can mark items `verified` before any PM or implementation
  model runs.
- The write firewall blocks mutations to `docs/PRD.md`, `docs/PLAN.md`, and any
  path outside the allowlist.
- Some PLAN targets are outside the executor's write allowlist, so those items
  depend on preexisting repo state or manual changes.
- The physical validation gate is stricter than a plain subprocess run because
  it allowlists command forms.
- The PLAN's Atomic Recovery Protocol is policy text. The current executor does
  not implement the full documented git patch/revert flow. Instead it retries
  with prompt context and then records `blocked` or `partial`.
- `GBNF_PM_NEXT` still encodes an `agent` field even though the JSON schema,
  Pydantic models, and contract tests no longer treat `agent` as part of the
  PM-next contract. On grammar-capable local backends, this mismatch is a real
  maintenance hazard.
- `quick-fix` only runs after quality failures. It is not a general-purpose
  repair stage for build or validation failures.

## Tools Analyzed But Not On The Live Execution Path

These Python files in `tools/` were inspected and intentionally omitted from
the runtime path above because they are not called by `start-loop2.ps1`,
`agent_manifest.json`, `tools/plan_exec.py`, or the build and quality workflow
chain:

- `tools/agent_call.py`
  Manual ad-hoc CLI for direct model prompts. It reuses prompts and
  `apply_writes`, but the main executor never imports or calls it.
- `tools/generate_verification_report.py`
  Used by `.cursor/workflows/verify-requirements.ps1` for the separate evidence
  pipeline, not by `plan_exec.py`.
- `tools/export_diagrams.py`
  Standalone documentation asset helper for Mermaid export.
- `tools/__init__.py`
  Package marker only.

## Practical Operator Workflow

Typical operator sequence today:

1. Start the router with `.\start-loop2.ps1`.
2. Run one executor pass with `python -m tools.plan_exec`.
3. Inspect `state/plan_state.json` and `logs/plan_execution_*.log`.
4. If needed, generate a report with
   `pwsh -ExecutionPolicy Bypass -File .cursor/workflows/plan-exec-report.ps1`.
5. Repeat step 2 until the desired PLAN slice is complete.
6. Run the separate requirements evidence pipeline when you need
   `docs/requirements-report.md` and `logs/verification/*.json`.

If you only want to reconcile the current repo against PLAN state without
calling models, use `python -m tools.plan_exec --state-only`.
