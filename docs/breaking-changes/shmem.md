# Shared Memory Breaking Changes

Freeze checkpoint: 2026-03-08 (Phase 0)

Frozen contract:

- `src/aetherflow/core/shared_memory_layout.py`
- ring slot count: `4`
- pixel labels: `BGR24`, `NV12`, `YUY2`, `MJPEG`, `RGB32`
- overflow policy: `DROP_OLDEST`
- metadata: `timestamp_ns`, `sequence_number`, `producer_cursor`,
  `consumer_cursor`, `overflow_count`

Change control:

- Any change to ring slot count, pixel labels, cursor semantics, slot
  alignment, or overflow behavior is a frozen-contract change and must be
  logged here first.
- Shared-memory changes also require a matching update to the contract tests
  and the docs before implementation can proceed.
- A human sign-off entry is required before merging a shared-memory ABI change.

Sign-off entry:

- Date: 2026-03-08
- Approver: qa.lead
- Scope: Phase 0 shared-memory freeze published.
- Change Class: freeze checkpoint
- Contract Path: src/aetherflow/core/shared_memory_layout.py
- Policy: Future changes require explicit human sign-off and a
  breaking-change entry before merge.
