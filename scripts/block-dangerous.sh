#!/usr/bin/env bash
set -euo pipefail

# Fail closed: a security gate must never silently allow when it cannot parse
# its input. Missing jq or an unparseable payload exits non-zero (deny) rather
# than emitting a permissive result.
command -v jq >/dev/null 2>&1 || {
  echo "block-dangerous: jq not available; refusing to continue" >&2
  exit 1
}

INPUT=$(cat)
TOOL_NAME=$(printf '%s' "$INPUT" | jq -er '.tool_name')

# Block dangerous terminal commands
if [ "$TOOL_NAME" = "runTerminalCommand" ]; then
  COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
  if echo "$COMMAND" | grep -qiE '(^|[^[:alnum:]_])(rm[[:space:]]+-rf|git[[:space:]]+push[[:space:]]+--force|drop[[:space:]]+table|truncate)([^[:alnum:]_]|$)'; then
    echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Destructive command blocked. Use explicit permission if intentional."}}'
    exit 0
  fi
fi

# Prevent direct editing of proto-generated files
if [ "$TOOL_NAME" = "editFiles" ] || [ "$TOOL_NAME" = "createFile" ]; then
  mapfile -t FILES < <(printf '%s' "$INPUT" | jq -r '.tool_input.files[]? // .tool_input.path // empty')
  for FILE in "${FILES[@]}"; do
    if echo "$FILE" | grep -qE '(_pb2\.py|_pb2_grpc\.py)$'; then
      echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Proto-generated files (_pb2.py, _pb2_grpc.py) must not be edited directly. Regenerate from .proto source instead."}}'
      exit 0
    fi
  done
fi

echo '{"continue":true}'