# Proto Breaking Changes

Freeze checkpoint: 2026-03-08 (Phase 0)

Frozen contract:

- `proto/capture.proto`
- service: `CaptureControl`
- RPCs: `StartCapture`, `StopCapture`, `ReportHeartbeat`,
  `ForwardWorkerLog`, `ReportPluginLoadResult`, `ExportDiagnostics`
- required status/load fields: `runtime_state`, `retry_budget_remaining`,
  `error_code`, `error_message`

Change control:

- Removing or renaming any message, field, RPC, or required status/load field
  is a breaking change and must be logged here first.
- Timeout or retry posture changes also require an explicit entry because the
  docs are part of the frozen Phase 0 control-plane contract.
- A human sign-off entry is required before merging a proto-surface change.

Sign-off entry:

- Date: 2026-03-08
- Approver: qa.lead
- Scope: Phase 0 proto freeze published.
- Change Class: freeze checkpoint
- Contract Path: proto/capture.proto
- Policy: Future changes require explicit human sign-off and a breaking-change
  entry before merge.
