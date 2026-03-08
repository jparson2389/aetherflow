# Auth Provider Sign-Off

Status: Pending human sign-off. Decision deadline: before `AF-05-01`.

Constraints:

- Must support OAuth-style providers.
- Provider-specific implementation is blocked until sign-off.

Fallback if deadline is missed:

- Implement only a provider-agnostic OAuth interface.
- Ship a disabled `MockOAuthProvider` for UI and integration-test coverage.
- Do not bind a real external provider without human approval.
