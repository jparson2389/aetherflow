# ABI Breaking Changes

Freeze checkpoint: 2026-03-08 (Phase 0)

Frozen contract:

- `include/plugin_system.hpp`
- `RuntimeState`: `RUNNING`, `DEGRADED`, `RECOVERING`, `FAILED`, `LOCKED`,
  `GRACE`
- signing baseline: `Authenticode`, `SHA-256`, `RSA-3072`
- trust policy: pinned trust root plus required publisher-chain validation

Change control:

- Any change to runtime-state enums, trust constants, or exported struct fields
  must be recorded here before implementation lands.
- A human sign-off entry is required before merging an ABI-affecting change.
- Until that sign-off entry exists, consumers must treat the Phase 0 ABI as
  immutable.

Sign-off entry:

- Date: 2026-03-08
- Approver: qa.lead
- Scope: Phase 0 ABI freeze published.
- Change Class: freeze checkpoint
- Contract Path: include/plugin_system.hpp
- Policy: Future changes require explicit human sign-off and a breaking-change
  log entry before merge.
