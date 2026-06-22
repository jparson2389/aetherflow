#!/usr/bin/env bash
# Audit logger. Fails closed: if the audit record cannot be parsed or written,
# the hook exits non-zero rather than silently allowing the action through.
set -euo pipefail

command -v jq >/dev/null 2>&1 || {
  echo "log-tool-use: jq not available; cannot write audit record" >&2
  exit 1
}

INPUT=$(cat)
TIMESTAMP=$(printf '%s' "$INPUT" | jq -r '.timestamp')
TOOL_NAME=$(printf '%s' "$INPUT" | jq -r '.tool_name')
SESSION_ID=$(printf '%s' "$INPUT" | jq -r '.sessionId')

AUDIT_LOG="${AUDIT_LOG:-audit.log}"
mkdir -p "$(dirname "$AUDIT_LOG")"
echo "[$TIMESTAMP] Session: $SESSION_ID | Tool: $TOOL_NAME" >> "$AUDIT_LOG"
echo '{"continue":true}'
