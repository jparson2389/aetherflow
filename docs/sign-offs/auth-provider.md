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

Failure UX and degraded-state model:

<!-- prettier-ignore-start -->
| Scenario | Host state | Online-resources surface | Worker state | Required behavior |
| --- | --- | --- | --- | --- |
| Sign-off unanswered for 24 hours | `RUNNING` | `LOCKED` until a real provider is approved | `RUNNING` with the disabled `MockOAuthProvider` only | Unblock downstream implementation with the provider-agnostic interface, keep the shell alive, and show approval-pending messaging instead of exposing a live provider |
| Provider-agnostic OAuth flow is temporarily unreachable | `RUNNING` | `DEGRADED` | `RECOVERING` | Retry within the normal session budget, keep cached catalog metadata readable, and surface remediation text without crashing the shell |
| Session is revoked or trust verification fails | `RUNNING` | `LOCKED` | `FAILED` for new authenticated actions | Block new downloads and installs on the next authenticated request, require re-authentication, and preserve existing diagnostics |
<!-- prettier-ignore-end -->

Downstream unblock rule:

- Agents may continue implementing the provider-agnostic interface, session
  handling, and UI lock states without waiting for provider selection.
- Only the provider-specific binding remains blocked pending human sign-off.
