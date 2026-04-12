## Relevant Files

- `docs/evidence/AF-00-05.md` - Must be refreshed with current-run timestamp, exact command, observed outcome, and gate-level proof mapping.
- `logs/verification/AF-00-05.json` - Must be updated with a `ran_at` timestamp to anchor freshness to the current validation run.
- `tests/contracts/test_prd_execution_readiness.py` - Needs a negative-path test proving omission of required fallback content fails the readiness check.
- `docs/sign-offs/auth-provider.md` - Target sign-off doc referenced by AC1; content verified adequate; no changes required.
- `docs/sign-offs/bundle-format.md` - Target sign-off doc referenced by AC1; content verified adequate; no changes required.

### Notes

- Item-scoped validation command: `uv run pytest tests/contracts/test_prd_execution_readiness.py -k plan`.
- Keep all remediation scoped to AF-00-05 evidence freshness and proof depth.
- Failed/warning Requirement Trace Matrix rows addressed: `EV1`, `EV2`.
- Medium finding addressed: `M-01`.
- Derived finding ids addressed separately: `DF-AF-00-05-01`, `DF-AF-00-05-02`, `DF-AF-00-05-03`.

## Instructions for Completing Tasks

**IMPORTANT:** As each task is completed, update this file by changing `- [ ]` to `- [x]`.

## Tasks

- [x] 0.0 Create feature branch
  - [x] 0.1 Create and checkout a new branch for this remediation work
- [x] 1.0 Restore evidence markdown freshness and traceability (`EV1`, `DF-AF-00-05-02`)
  - [x] 1.1 Run `uv run pytest tests/contracts/test_prd_execution_readiness.py -k plan -v` and record the current observed outcome (pass count and exit code).
  - [x] 1.2 Add a `## Current Run Traceability` section to `docs/evidence/AF-00-05.md` with: exact validation command, executed-at UTC timestamp, and observed outcome.
  - [x] 1.3 Add a `## Completion Gate Linkage` section (or equivalent) mapping each of the three completion gates to the concrete test(s) and files that prove them.
- [x] 2.0 Add run timestamp to verification JSON (`EV2`, `DF-AF-00-05-01`)
  - [x] 2.1 Add a `ran_at` field (ISO-8601 UTC string) to `logs/verification/AF-00-05.json` matching the timestamp captured in Task 1.1.
  - [x] 2.2 Verify the JSON is still parseable and all existing fields (validation_commands, validation_results, exit_codes, requirement_links) remain intact.
- [x] 3.0 Add negative-path test for sign-off fallback omission (`M-01`, `DF-AF-00-05-03`)
  - [x] 3.1 In `tests/contracts/test_prd_execution_readiness.py`, add `test_plan_signoff_packet_without_fallback_is_rejected` that builds a synthetic sign-off doc string missing the `Fallback` keyword and asserts the content check raises `AssertionError`.
  - [x] 3.2 Re-run `uv run pytest tests/contracts/test_prd_execution_readiness.py -k plan -v` and confirm the new negative-path test is selected and passes.
  - [x] 3.3 Update `docs/evidence/AF-00-05.md` and `logs/verification/AF-00-05.json` with the refreshed outcome reflecting the new test.
