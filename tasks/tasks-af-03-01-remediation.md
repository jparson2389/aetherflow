## Relevant Files

- `docs/evidence/AF-03-01.md` - Evidence pack requiring reviewer sign-off (M-01).
- `logs/verification/AF-03-01.json` - Verification artifact recording pending sign-off status (M-01).
- `tests/integration/test_capture_opencv.py` - Integration tests for OpenCV capture plugin; needs coverage for dropped-frame tracking and conservative fallback branch (M-02, L-01).
- `tests/integration/test_capture_stability.py` - Stability/metrics tests; `dropped=True` path for session snapshot not covered (M-02).
- `src/aetherflow/vision/opencv_capture.py` - `WindowsOpenCVCaptureProbe._mode_allowed_for_device` conservative fallback branch (fps in {30,60}, unknown VID/PID) is not test-covered (M-02).

### Notes

- Addresses requirements: M-01 (governance gap — pending reviewer sign-off), M-02 (untested code paths: conservative fallback and dropped-frame recording), L-01 (weak structural assertion).
- Item-scoped validation command: `uv run pytest tests/integration/test_capture_opencv.py tests/ui/test_capture_mode_matrix.py tests/integration/test_capture_stability.py -v`
- `App-Testable: false` — all tests use injected fakes or unit-level fixtures. Do not require physical hardware.
- Failed requirement IDs addressed: M-01, M-02, L-01.

## Instructions for Completing Tasks

**IMPORTANT:** As each task is completed, update this file by changing `- [ ]` to `- [x]`.

## Tasks

- [ ] 0.0 Create feature branch
  - [ ] 0.1 Create and checkout a new branch: `git checkout -b fix/af-03-01-test-coverage`

- [ ] 1.0 Obtain reviewer sign-off on evidence pack (M-01)
  - [ ] 1.1 Have a human reviewer read `docs/evidence/AF-03-01.md` and confirm that the proof matrix, performance artifact measurements, and gap disclosures are accurate against the current codebase
  - [ ] 1.2 Update `docs/evidence/AF-03-01.md`: set `Reviewer Status: approved`, fill in `Reviewer:` and `Reviewed At:` fields, set `Sign-Off Status: approved`
  - [ ] 1.3 Update `logs/verification/AF-03-01.json`: set `"reviewer_status": "approved"`, `"approved_by": "<reviewer>"`, remove the `"Reviewer sign-off is not approved"` entry from `gaps`

- [x] 2.0 Cover conservative fallback branch for unknown VID/PID devices (M-02)
  - [x] 2.1 In `tests/integration/test_capture_opencv.py`, add `test_opencv_probe_conservative_fallback_for_unknown_device`: construct a `WindowsOpenCVCaptureProbe` with a device whose `device_id` has no matching VID/PID in `_DEVICE_CAPABILITY_RULES`; call `_fallback_modes_for(device)` and assert that only 30fps and 60fps modes at ≤1920×1080 are returned (no 120/144/240 entries)
  - [x] 2.2 Assert in that test that the returned modes include at least `(1920, 1080, 30)` and `(1920, 1080, 60)`, and that no entry has `capture_fps in {120, 144, 240}`

- [x] 3.0 Cover dropped-frame recording in session snapshot (M-02)
  - [x] 3.1 In `tests/integration/test_capture_opencv.py`, add `test_opencv_capture_records_dropped_frames_in_session_metrics`: call `start_capture` for a supported mode, call `record_capture_sample(..., dropped=True)` a known number of times alongside normal frames, then call `stop_capture` and assert that `metrics.dropped_frames == expected_count`
  - [x] 3.2 Confirm `metrics.frames_total == delivered + dropped` in the same test to validate the denominator used in `drop_rate`

- [x] 4.0 Replace structural assertion in weak test (L-01)
  - [x] 4.1 In `tests/integration/test_capture_opencv.py`, in `test_opencv_capture_enumerates_supported_modes_per_device`, remove `assert devices[0].device_id.startswith('USB\\')` (structural check on fake data)
  - [x] 4.2 Replace with a behavioral assertion: assert that calling `plugin.supported_modes(devices[0].stable_id)` returns a non-empty list, and that all returned modes have `capture_width > 0` and `capture_fps > 0`

- [x] 5.0 Verify remediation passes validation gate
  - [x] 5.1 Run `uv run pytest tests/integration/test_capture_opencv.py tests/ui/test_capture_mode_matrix.py tests/integration/test_capture_stability.py -v` and confirm all tests pass with exit code 0
  - [x] 5.2 Run `uv run python -m tools.check_quality` and confirm the full quality gate passes
