## Relevant Files

- `docs/PLAN.md` - Canonical acceptance criteria and entry point for `AF-02-02`.
- `docs/evidence/AF-02-02.md` - Must match PLAN AC text and provable claims.
- `src/aetherflow/output/virtual_controller.py` - Output driver service to wire into the app.
- `src/aetherflow/ui/panels/driver_status_panel.py` - Panel model; must be used from live UI.
- `src/aetherflow/ui/app_window.py` - Likely attachment point for driver status UI.
- `src/aetherflow/ui/router.py` / `src/aetherflow/ui/shell.py` - Navigation/shell integration as appropriate.
- `tests/ui/test_driver_panel.py` - Extend or add tests proving production import path and shell visibility.
- `tests/integration/test_output_virtualization.py` - Service-level proofs; keep aligned with PLAN.

### Notes

- Failed requirement IDs addressed: **AC1**, **AC2**, **CG1**, **C1**, **C2**, **H1** (and closure of **M1** if full-app isolation is required for CG2).
- Derived findings addressed: **DF-UI-01**, **DF-UI-02**.
- Run item-scoped validation after changes:  
  `uv run pytest tests/integration/test_output_virtualization.py tests/ui/test_driver_panel.py`  
  plus any new tests added for UI wiring.

## Instructions for Completing Tasks

**IMPORTANT:** As each task is completed, update this file by changing `- [ ]` to `- [x]`.

## Tasks

- [x] 0.0 Create feature branch
  - [x] 0.1 Create and checkout a new branch for this remediation work
- [x] 1.0 Align evidence with canonical PLAN and remove unproven claims (**C2**, **H1**)
  - [x] 1.1 Edit `docs/evidence/AF-02-02.md` so AC1 and AC2 match `docs/PLAN.md` verbatim (reversible/survives failure; panel reflects output-plugin state).
  - [x] 1.2 Remove or replace the phrase “visible in the shell” unless a test proves shell integration (**H1**).
  - [x] 1.3 Update the proof matrix rows to reference the same AC ids and proof scope as PLAN.
- [x] 2.0 Wire output virtualization and driver panel into the running application (**C1**, **AC2**, **CG1**, **DF-UI-01**, **DF-UI-02**)
  - [x] 2.1 Instantiate or obtain `VirtualControllerService` from the application composition layer (bootstrap or app shell) so it is part of runtime, not tests-only (**DF-UI-01**).
  - [x] 2.2 Render or connect `DriverStatusPanelModel` (or a thin view that consumes it) from the real driver status panel / main window path declared as the entry point (**AC2**, **CG1**).
  - [x] 2.3 Ensure install/repair/mask actions invoked from the panel (or documented equivalent UI actions) call into `VirtualControllerService` so flows are functional through the UI surface (**CG1**).
- [x] 3.0 Strengthen tests so UI wiring cannot regress silently (**AC1**, **AC2**, **H1**)
  - [x] 3.1 Add a test that imports the same code path the app uses to build the driver status UI and asserts the panel/model is reachable from that path (**AC2**).
  - [x] 3.2 Add a UI or integration test that fails if `VirtualControllerService` is not registered with the shell or main window (choose the narrowest stable harness available) (**AC1**, **H1**).
  - [ ] 3.3 Optionally add coverage for CG2 across app boundaries if product requires proof beyond service tests (**M1**).
- [x] 4.0 Regenerate verification artifacts
  - [x] 4.1 Run `uv run python -m tools.verify_requirements` (or the repo’s canonical regrade command) after evidence and tests are updated.
  - [x] 4.2 Confirm `logs/verification/AF-02-02.json` reflects updated proof and no longer implies UI completion without wiring (**H2**).
