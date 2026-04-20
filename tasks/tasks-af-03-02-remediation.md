## Relevant Files

- `src/aetherflow/ui/panels/render_mode_panel.py` - RenderModePanelModel: the data model that must be wired to the runtime capture/render path (currently isolated).
- `src/aetherflow/ui/panels/capture_panel.py` - CapturePanelModel: only references OpenCVCapturePlugin; does not hold render mode state or connect to premium backends.
- `src/aetherflow/ui/bootstrap.py` - Shell bootstrap: builds routes and panels; does not wire render mode or premium capture backends into any route.
- `src/aetherflow/ui/shell.py` - ShellModel: does not carry a render mode field or reference premium backends.
- `src/aetherflow/vision/mf_capture.py` - MediaFoundationCapturePlugin: premium backend, not referenced in runtime execution path.
- `src/aetherflow/vision/ds_capture.py` - DirectShowCapturePlugin: premium DS backend, not referenced in runtime execution path.
- `src/aetherflow/core/services.py` - AppServices: may need a render_mode field or accessor to carry active render mode state.
- `tests/ui/test_render_modes.py` - Existing render mode tests: test the data model in isolation; must be supplemented with wiring assertion tests.
- `tests/e2e/test_capture_premium_e2e.py` - Existing e2e tests: test_120fps_mf_path_through_ui_mode_list calls render mode panel but does not connect it to capture runtime — needs real wiring test.
- `docs/evidence/AF-03-02.md` - Evidence markdown: contains a test count error (6 listed, 7 exist), claims no unresolved gaps (contradicts verification JSON), and has stale run timestamp.
- `logs/verification/AF-03-02.json` - Verification JSON: records ac-coverage-gap and review/sign-off-gap that must be resolved.

### Notes

- Failed requirements addressed by this file: GATE-2 (render mode UI wired to runtime selection), H-02 (ac-coverage-gap in verification JSON unresolved), M-01 (evidence test count mismatch), M-02 (reviewer sign-off pending).
- The render mode wiring does not require live hardware. It requires that `RenderModePanelModel.active_mode_id` is consumed by at least one runtime component (capture session config, worker config, or service layer) such that selecting `render.gpu` vs `render.cpu` produces an observable downstream difference in state.
- The work item declares `App-Testable: false`, so live UI widget wiring is not required. The wiring must be demonstrated at the model/service layer and proven by a test that crosses the panel model to a runtime component.
- Run item-scoped validation with:
  `uv run pytest tests/integration/test_capture_premium_gating.py tests/ui/test_render_modes.py tests/ui/test_capture_fallback_actions.py tests/integration/test_capture_120fps_path.py tests/e2e/test_capture_premium_e2e.py -v`
- Always run `uv run ruff check .` before marking any task complete.

## Instructions for Completing Tasks

**IMPORTANT:** As each task is completed, update this file by changing `- [ ]` to `- [x]`.

## Tasks

- [ ] 0.0 Create feature branch
  - [ ] 0.1 Create and checkout a new branch: `git checkout -b fix/af-03-02-render-mode-wiring`

- [ ] 1.0 Wire render mode selection into the runtime capture/service path (addresses GATE-2, H-02)
  - [ ] 1.1 Add an `active_render_mode` field (type `str`, default `'render.cpu'`) to `AppServices` or to the capture session configuration so that the current render mode can be read at runtime by backends or workers.
  - [ ] 1.2 Update `RenderModePanelModel.select()` — or add a companion method — so that applying a render mode selection propagates the `active_mode_id` to the `AppServices` render mode field (or equivalent runtime holder).
  - [ ] 1.3 Update `CapturePanelModel` (or the relevant capture entry point) to accept a render mode argument and pass it through to the capture session or worker configuration; this establishes the minimum cross-boundary link.
  - [ ] 1.4 Alternatively, if the architecture prefers a simpler surface: add `render_mode` as a parameter to `start_capture()` on `MediaFoundationCapturePlugin` / `OpenCVCapturePlugin` so that a render mode selection has a visible, assertable effect on the resulting `CaptureSession`.

- [ ] 2.0 Add a cross-boundary test that proves render mode selection affects runtime (addresses GATE-2 proof gap)
  - [ ] 2.1 In `tests/ui/test_render_modes.py` or `tests/integration/`, add a test that:
    - Creates a render panel model with `RenderModePanelModel.default()`.
    - Calls `.select('render.gpu')` to obtain the updated panel.
    - Passes the `active_mode_id` from the updated panel to a capture or service layer call.
    - Asserts that the downstream state (capture session config, worker param, service field, or session attribute) reflects the selected mode.
  - [ ] 2.2 Update `tests/e2e/test_capture_premium_e2e.py::TestHighFpsEntitlementChainWithUI::test_120fps_mf_path_through_ui_mode_list` so that the render mode selection produces an observable effect on the capture session (assert that the session carries the selected render mode, or that the capture config differs between CPU and GPU selection).

- [ ] 3.0 Resolve the self-reported ac-coverage-gap in the verification JSON (addresses H-02)
  - [ ] 3.1 Verify that at least one runtime code path (shell bootstrap, capture panel model, or services) instantiates or references `MediaFoundationCapturePlugin` or `DirectShowCapturePlugin`, OR document explicitly in the evidence that entry-point instantiation is deferred to the C++ host (with a clear rationale).
  - [ ] 3.2 Update `logs/verification/AF-03-02.json` to either remove the ac-coverage-gap (if the wiring from Task 1 closes it) or retain it with an explicit resolution note.

- [ ] 4.0 Fix evidence markdown test count and stale run timestamp (addresses M-01)
  - [ ] 4.1 Update `docs/evidence/AF-03-02.md` test coverage summary for `tests/integration/test_capture_120fps_path.py` to list all 7 tests (add `test_sustained_120fps_throughput` at line 245 which is currently omitted).
  - [ ] 4.2 Re-run the validation command and update the `Executed At` timestamp and observed outcome in `docs/evidence/AF-03-02.md` to reflect a post-wiring run.

- [ ] 5.0 Reconcile evidence markdown "no unresolved gaps" claim against verification JSON (addresses H-02, M-01)
  - [ ] 5.1 After Task 1–3 are complete, review `docs/evidence/AF-03-02.md` "Unresolved Gaps" section and replace with an accurate statement that either confirms all gaps are closed or lists remaining gaps with their status.
  - [ ] 5.2 Ensure the Completion Gate Verification section for GATE-2 cites the new cross-boundary test added in Task 2.

- [ ] 6.0 Obtain reviewer sign-off (addresses M-02)
  - [ ] 6.1 Update `Reviewer Status` in `docs/evidence/AF-03-02.md` from `pending` to the reviewer name and date after human review.
  - [ ] 6.2 Update `approved_by` in `logs/verification/AF-03-02.json` from `null` to the approver identifier.
