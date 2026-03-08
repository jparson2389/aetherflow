# Auth Provider Sign-Off

Status: Pending human sign-off. Decision deadline: before `AF-05-01`.
Blocking phase: Phase 5 Online Resources.

Constraints:

- Must support OAuth-style providers.
- Provider-specific implementation is blocked until sign-off.

SLA and re-poll guidance:

- If no response is received within 24 hours, proceed with the fallback.
- Re-poll once per day until a human decision is recorded.

Fallback if deadline is missed:

- Implement only a provider-agnostic OAuth interface.
- Ship a disabled `MockOAuthProvider` for UI and integration-test coverage.
- Do not bind a real external provider without human approval.
