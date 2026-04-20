## Relevant Files

- `tasks/tasks-commit-hygiene-change-splitting.md` - Execution checklist for the
  commit-splitting cleanup.
- `PLAN.md` - Intentional branch-owned gap-closure plan that should stay in the
  plan/restructure commit.
- `plan/process-verification-authority-2.md` - Machine-readable plan artifact
  that should be evaluated as durable branch content, not disposable scratch.
- `tasks/tasks-rework-plan.md` - Existing rework-plan task file that belongs in
  the plan/restructure bucket.
- `CLAUDE.md` - Repo instructions file currently staged and likely part of the
  docs/rules bucket unless kept with plan docs.
- `AGENTS.md` - Repo coding rules update candidate for the docs/rules bucket.
- `.gitignore` - Primary place to add ignore rules for disposable local
  artifacts such as `logs/audit/`.
- `docs/evidence/AF-*.md` - Verification evidence packs that should be grouped
  into an evidence/documentation commit or folded into tightly coupled feature
  commits.
- `docs/sign-offs/auth-provider.md` - Sign-off doc that belongs in the docs
  housekeeping bucket.
- `docs/sign-offs/bundle-format.md` - Sign-off doc that belongs in the docs
  housekeeping bucket.
- `docs/verify-requirements-pipeline.md` - Verification workflow doc that
  belongs in the docs housekeeping bucket.
- `proto/capture.proto` - Frozen control-plane contract that must be isolated in
  its own boundary-focused commit if intentionally changed.
- `src/aetherflow/core/shared_memory_layout.py` - Shared-memory boundary file
  that should be reviewed alongside proto contract changes.
- `src/aetherflow/proto/capture_pb2.py` - Generated stub that must never be
  hand-edited and may need regeneration if the proto changes.
- `src/aetherflow/proto/capture_pb2_grpc.py` - Generated gRPC stub that must
  never be hand-edited and may need regeneration if the proto changes.
- `tools/build_assets.py` - Canonical asset/stub build entrypoint to use after
  intentional proto changes.
- `logs/bundle_install_report.json` - Generated log/report file that should be
  explicitly discarded unless intentionally shipped.
- `logs/native_harness_build.log` - Generated log file that should be
  explicitly discarded unless intentionally shipped.
- `logs/quality-gate.log` - Generated log file that should be explicitly
  discarded unless intentionally shipped.
- `logs/audit/` - Timestamped audit output that is disposable by default unless
  a specific report is explicitly promoted into durable evidence.
- `scripts/start_loop3.sh` - Untracked script that should be classified as
  intentional tooling or excluded from the branch cleanup.

### Notes

- Use `git --no-pager status --short --branch`, `git --no-pager diff --stat`,
  and `git --no-pager diff --cached --stat` to keep the staged and unstaged
  buckets visible while splitting work.
- Prefer `git add -p` and path-based staging over staging everything at once.
- If `proto/capture.proto` is intentionally changed, run
  `uv run python -m tools.build_assets` before staging downstream runtime work.
- Never hand-edit `src/aetherflow/proto/*_pb2.py` or
  `src/aetherflow/proto/*_pb2_grpc.py`.
- Treat `logs/audit/**` as disposable by default. Promote only stable
  conclusions into `PLAN.md`, `docs/`, evidence packs, or verification JSON.

## Instructions for Completing Tasks

**IMPORTANT:** As you complete each task, you must check it off in this markdown
file by changing `- [ ]` to `- [x]`. This helps track progress and ensures you
don't skip any steps.

## Tasks

- [x] 0.0 Create feature branch
  - [x] 0.1 Confirm whether work should continue on `restructure-plan` or move
        to a fresh feature branch for the cleanup.
        **Decision:** Continue on `restructure-plan`. Branch name matches the work,
        staged set already holds the plan/restructure files, no new branch needed.
  - [x] 0.2 If a new branch is needed, create and checkout it before changing
        the index layout.
        **Result:** No new branch created — continuing on `restructure-plan`.
- [x] 1.0 Preserve the current staged plan/restructure set as an isolated commit candidate
  - [x] 1.1 Snapshot the currently staged diff so it can be restored exactly if
        later staging work disturbs the index.
        **Snapshot:** 4 files — CLAUDE.md (+27/-0 net), PLAN.md (+287/-513), REWORK_PLAN.md (deleted -342), tasks/tasks-rework-plan.md (+0/-184 net). Saved to /tmp/staged_snapshot.txt.
  - [x] 1.2 Verify that the staged set still contains only the intended
        plan/restructure files: `PLAN.md`, `tasks/tasks-rework-plan.md`,
        deletion of `REWORK_PLAN.md`, and any explicitly approved companion file.
        **Result:** Set is correct. CLAUDE.md is extra — see 1.3. Also need to ADD `plan/process-verification-authority-2.md` (untracked).
  - [x] 1.3 Decide whether `CLAUDE.md` stays with the plan/restructure commit or
        moves to the docs/rules commit.
        **Decision:** CLAUDE.md → **docs/rules bucket**. Changes are dev-env platform corrections (WSL→Windows), markdown-table prettier rule, and proto stub enforcement note — all repo-rules content, not plan restructuring.
  - [x] 1.4 Define the commit message scope and intent for the preserved staged
        set before mixing in any unstaged paths.
        **Commit message:** `refactor(plan): restructure PLAN.md as gap-closure plan, retire REWORK_PLAN.md`
- [x] 2.0 Classify changed files into commit buckets and identify disposable artifacts
  - [x] 2.1 Review unstaged tracked files and group each path into one of these
        buckets: docs/rules, boundary/proto, runtime, evidence/docs, tests,
        tooling, or disposable output.
        **Buckets:**
        - **plan/restructure** (commit A): PLAN.md, REWORK_PLAN.md(del), tasks/tasks-rework-plan.md, plan/process-verification-authority-2.md
        - **docs/rules** (commit B): CLAUDE.md, AGENTS.md, .markdownlint.jsonc, .prettierignore, docs/verify-requirements-pipeline.md, docs/dev/generate-tasks.md
        - **evidence/docs** (commit C): docs/evidence/AF-*.md (14 files), docs/sign-offs/auth-provider.md, docs/sign-offs/bundle-format.md, docs/PLAN.md, docs/breaking-changes/abi.md, docs/breaking-changes/proto.md, docs/breaking-changes/shmem.md
        - **boundary/proto** (commit D): proto/capture.proto, src/aetherflow/core/shared_memory_layout.py, docs/proto/capture.md
        - **core runtime** (commit E): src/aetherflow/core/capture_metrics.py, entitlements.py, profile_persistence.py, profiles.py, settings.py, verification_report.py
        - **plugin+security** (commit F): src/aetherflow/plugins/catalog.py, registry.py, trust.py, src/aetherflow/security/manifest_signing.py
        - **I/O+vision** (commit G): src/aetherflow/input/mapping.py, src/aetherflow/output/device_masking.py, virtual_controller.py, src/aetherflow/vision/ds_capture.py, mf_capture.py, opencv_capture.py
        - **UI** (commit H): src/aetherflow/ui/ (all 9 files)
        - **tests** (commit I): all tests/ files + untracked tests/e2e/test_capture_premium_e2e.py
        - **tooling** (commit J): tools/apply_writes.py, build_assets.py, plan_exec.py, shell_utils.py
        - **gitignore+cleanup** (commit K): .gitignore (add logs/audit/ rule), discard log churn
        - **disposable/discard**: logs/bundle_install_report.json, logs/native_harness_build.log, logs/quality-gate.log
  - [x] 2.2 Review untracked files and decide whether each one is intentional
        repo content, a candidate for `.gitignore`, or local scratch to drop.
        - `logs/audit/` → disposable, add to .gitignore
        - `plan/process-verification-authority-2.md` → intentional, include in commit A
        - `scripts/start_loop3.sh` → WSL/zsh local scratch (references "Aetherlink 4080 Super WSL Native"), exclude from all commits
        - `tests/e2e/test_capture_premium_e2e.py` → intentional new test, include in commit I
  - [x] 2.3 Mark `logs/audit/**` as disposable by default, with explicit
        exceptions only for reports intentionally promoted into durable evidence.
        **Decision:** logs/audit/ is disposable. No exceptions — no audit reports have been promoted to docs/evidence/. Will add to .gitignore.
  - [x] 2.4 Record the final bucket assignment for any ambiguous files so they do
        not drift between commits during staging.
        **Ambiguous resolutions:**
        - `docs/PLAN.md` → evidence/docs (commit C), not plan/restructure — it's the machine-readable docs-side plan
        - `docs/breaking-changes/*.md` → evidence/docs (commit C), not boundary/proto — they document the change but don't define the contract
        - `CLAUDE.md` → docs/rules (commit B), not plan/restructure
        - `scripts/start_loop3.sh` → excluded entirely (WSL scratch, not repo content)
- [x] 3.0 Separate plan, docs, sign-off, and evidence updates into reviewable documentation commits
  - [x] 3.1 Stage the intentional plan artifacts together: root `PLAN.md`,
        `plan/process-verification-authority-2.md`,
        `tasks/tasks-rework-plan.md`, and `REWORK_PLAN.md` deletion if they still
        belong in one commit.
        **Commit A:** `refactor(plan): restructure PLAN.md as gap-closure plan, retire REWORK_PLAN.md` (b7c13f0)
  - [x] 3.2 Stage repo rules and documentation housekeeping separately, including
        `AGENTS.md`, `.markdownlint.jsonc`, `.prettierignore`,
        `docs/verify-requirements-pipeline.md`, and sign-off documents.
        **Commit B:** `docs(rules): update CLAUDE.md, AGENTS.md, and verification workflow docs` (04c7e0b)
        Note: sign-off documents moved to evidence commit (C) to keep rules commit clean.
  - [x] 3.3 Gather `docs/evidence/AF-*.md` updates into a dedicated evidence
        commit unless a specific pack must ship atomically with a code change.
        **Commit C:** `docs(evidence): update AF-* evidence packs, sign-offs, and breaking-change docs` (ba17e35)
  - [x] 3.4 Re-check that no runtime, proto, test, or generated-log changes have
        leaked into the documentation commits.
        **Verified clean:** commits A/B/C contain only docs/rules/plan files.
- [x] 4.0 Isolate frozen-contract and shared-memory boundary changes behind an explicit rebuild gate
  - [x] 4.1 Review whether `proto/capture.proto` changes are intentional and
        allowed for this branch, given the repo’s frozen-contract rules.
        **Finding:** proto changes are comment-only (doc strings on messages/service). No wire/field changes. Intentional and safe.
  - [x] 4.2 If the proto change is intentional, stage only the boundary-related
        files together: `proto/capture.proto`,
        `src/aetherflow/core/shared_memory_layout.py`, `docs/proto/capture.md`,
        and tightly coupled contract tests.
        **Commit D:** `feat(boundary): add doc comments to capture.proto, update pixel-format enum` (6b47f41)
        Note: contract tests stay in the tests commit (I) to keep boundary commit focused.
  - [x] 4.3 Run `uv run python -m tools.build_assets` if the proto changed, and
        confirm any regenerated artifacts are handled according to repo rules.
        **Result:** Stub rebuild NOT required — proto changes are comment-only. Generated stubs unchanged.
  - [x] 4.4 Keep the boundary commit free of unrelated runtime, evidence, or
        tooling churn.
        **Verified:** commit D contains only proto/capture.proto, shared_memory_layout.py, docs/proto/capture.md.
- [x] 5.0 Split runtime implementation, tests, and tooling changes into coherent commit groups
  - [x] 5.1 Stage runtime implementation files from `src/aetherflow/core/`,
        `plugins/`, `output/`, `vision/`, and `ui/` in cohesive feature slices
        rather than one giant catch-all commit.
        **Commit E:** core runtime (verification_report, capture_metrics, profiles, entitlements, settings, profile_persistence) (a4c7de3)
        **Commit F:** plugin+security (catalog, registry, trust, manifest_signing) (9b90f03)
        **Commit G:** I/O+vision (mapping, device_masking, virtual_controller, ds_capture, mf_capture, opencv_capture) (f8dee5c)
        **Commit H:** UI (app_window, shell, router, panels, status_hud, bootstrap) (2e51ddc)
  - [x] 5.2 Decide which tests should stay with the runtime or boundary commits
        and which can stand in a dedicated test/verification commit.
        **Decision:** All tests in a single dedicated commit I — the tests span multiple feature areas and boundary concerns; splitting them per feature commit would create unwieldy partial staging with no atomic value.
        **Commit I:** all tests/ (41 files, +2626/-214) (72e947e)
  - [x] 5.3 Stage tooling changes under `tools/` separately unless they are
        inseparable from a specific feature or boundary commit.
        **Commit J:** tools/ (apply_writes, build_assets, plan_exec, shell_utils) (058613e)
  - [x] 5.4 Classify `scripts/start_loop3.sh` as intentional tooling or leave it
        out of the commit sequence entirely.
        **Decision:** Excluded. Script is a WSL/zsh local runner ("Aetherlink 4080 Super WSL Native"). Not repo content — will remain untracked.
- [x] 6.0 Finalize `.gitignore` updates, discard non-shipping log churn, and prepare the exact commit sequence
  - [x] 6.1 Add the minimal `.gitignore` updates needed for disposable
        local/generated artifacts, starting with `logs/audit/` if that policy is
        being codified in the branch.
        **Done:** Added `logs/audit/` to .gitignore in the "Generated logs" section.
        **Commit K:** `chore(gitignore): add logs/audit/ to ignore disposable audit output` (37c3441)
  - [x] 6.2 Explicitly discard non-shipping generated log/report changes from
        `logs/bundle_install_report.json`, `logs/native_harness_build.log`, and
        `logs/quality-gate.log` unless one is intentionally part of the branch.
        **Done:** `git restore` applied to all three. Changes were accumulated run output, not intentional branch content. Working tree now matches HEAD for all three files.
  - [x] 6.3 Write the exact commit order, staging commands, and file groups so
        the split can be executed repeatably without re-deciding scope midstream.
        **Final commit sequence (all executed):**
        - A (b7c13f0): `refactor(plan)` — PLAN.md, REWORK_PLAN.md(del), tasks/tasks-rework-plan.md, plan/
        - B (04c7e0b): `docs(rules)` — CLAUDE.md, AGENTS.md, .markdownlint.jsonc, .prettierignore, docs/verify-requirements-pipeline.md, docs/dev/generate-tasks.md
        - C (ba17e35): `docs(evidence)` — 14 AF-* evidence packs, sign-offs, docs/PLAN.md, breaking-change docs
        - D (6b47f41): `feat(boundary)` — proto/capture.proto, shared_memory_layout.py, docs/proto/capture.md
        - E (a4c7de3): `feat(core)` — core/ runtime files (6 files)
        - F (9b90f03): `feat(plugins)` — plugins/ + security/ (4 files)
        - G (f8dee5c): `feat(io+vision)` — input/, output/, vision/ (6 files)
        - H (2e51ddc): `feat(ui)` — ui/ (9 files)
        - I (72e947e): `test` — all tests/ (41 files)
        - J (058613e): `chore(tools)` — tools/ (4 files)
        - K (37c3441): `chore(gitignore)` — .gitignore (+logs/audit/)
  - [x] 6.4 Perform one final `git status` review to confirm every remaining path
        is either assigned to a commit, ignored, or intentionally left out.
        **Result:** Working tree is clean. Only `scripts/start_loop3.sh` remains untracked (WSL/zsh scratch, intentionally excluded). All 104 changed files are committed. logs/audit/ is now ignored. logs/*.log changes discarded.
