# Bundle Format Sign-Off

Status: Pending human sign-off. Decision deadline: before `AF-04-02`.
Blocking phase: Phase 4 Environment Management.

Constraints:

- Aetherflow-owned term and extension.
- Signed manifest plus SHA-256 validation.
- One-click install with streamed logs.

Fallback if deadline is missed:

- Implement a signed archive with internal `bundle.json` metadata.
- Keep the external bundle extension unfrozen until human sign-off.
- Do not block environment-manager implementation on naming alone.
