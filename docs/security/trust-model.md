# Trust Model

## Summary

Aetherflow uses a split trust model:

- Native plugin binaries are trusted with Windows Authenticode validation.
- JSON manifests for bundles and online resources are trusted with detached
  Ed25519 signatures and a pinned application trust store.

This document supplements the implementation without changing the frozen PRD or
contract documents.

## Native Plugins

- External plugins must provide an artifact path.
- Trust is derived from the artifact on disk, not from manifest flags.
- Verification is fail-closed and returns explicit denial reasons such as
  `unsigned`, `revoked`, `expired`, `hash-mismatch`, or
  `untrusted-publisher`.
- Built-in plugins remain explicit first-party entries and do not rely on
  external-discovery trust metadata.

## Bundle And Resource Manifests

- Detached signatures are verified over canonical JSON payloads.
- The manifest trust store is loaded from `assets/trust/manifest_keys.json` by
  default and can be overridden through settings.
- Verification fails closed on missing trust store, missing key id, unknown key,
  malformed signature, or payload tampering.

## Authorization And Export Safety

- Route discovery and route activation are both permission-checked.
- Admin panel construction requires `Admin/Operator`.
- Diagnostics and audit metadata are redacted before export.
- Audit records are appended to `logs/admin_audit.ndjson` in this repo pass.
