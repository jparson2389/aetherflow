# Bundle Format Sign-Off

Status: Pending human sign-off. Decision deadline: before `AF-04-02`.
Blocking phase: Phase 4 Environment Management.

Constraints:

- Aetherflow-owned term and extension.
- Signed manifest plus SHA-256 validation.
- One-click install with streamed logs.

SLA and re-poll guidance:

- If no response is received within 24 hours, proceed with the fallback.
- Re-poll once per day until a human decision is recorded.

Fallback if deadline is missed:

- Implement a signed archive with internal `bundle.json` metadata.
- Keep the external bundle extension unfrozen until human sign-off.
- Do not block environment-manager implementation on naming alone.

Failure UX and degraded-state model:

<!-- prettier-ignore-start -->
| Scenario                                                  | Host state | Environment-management surface               | Worker state                                    | Required behavior                                                                                                                      |
|-----------------------------------------------------------|------------|----------------------------------------------|-------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------|
| Naming sign-off unanswered for 24 hours                   | `RUNNING`  | `RUNNING` with fallback archive semantics    | `RUNNING`                                       | Proceed with the signed archive plus internal `bundle.json`, preserve one-click install UX, and defer only the external extension name |
| Manifest, digest, or signature verification fails         | `RUNNING`  | `FAILED` only for the active install attempt | `FAILED` for that install transaction           | Reject activation, quarantine the invalid bundle, stream failure logs, and keep unrelated shell surfaces available                     |
| Bundle is valid but required environment validation fails | `RUNNING`  | `DEGRADED`                                   | `RECOVERING` while repair guidance is generated | Preserve the staged bundle, expose actionable repair guidance, and allow manual retry without blocking other features                  |
<!-- prettier-ignore-end -->

Downstream unblock rule:

- Agents may implement signed-archive install, SHA-256 verification, streamed
  logs, and `bundle.json` metadata handling now.
- Only the public-facing bundle extension name remains blocked pending human
  sign-off.
