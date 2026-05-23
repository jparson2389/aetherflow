#!/usr/bin/env bash
INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name')

# Block dangerous terminal commands
if [ "$TOOL_NAME" = "runTerminalCommand" ]; then
  COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
  if echo "$COMMAND" | grep -qE '(rm\s+-rf|git\s+push\s+--force|DROP\s+TABLE|truncate)'; then
    echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Destructive command blocked. Use explicit permission if intentional."}}'
    exit 0
  fi
fi

# Prevent direct editing of proto-generated files
if [ "$TOOL_NAME" = "editFiles" ] || [ "$TOOL_NAME" = "createFile" ]; then
  FILES=$(echo "$INPUT" | jq -r '.tool_input.files[]? // .tool_input.path // empty')
  for FILE in $FILES; do
    if echo "$FILE" | grep -qE '(_pb2\.py|_pb2_grpc\.py)$'; then
      echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Proto-generated files (_pb2.py, _pb2_grpc.py) must not be edited directly. Regenerate from .proto source instead."}}'
      exit 0
    fi
  done
fi

echo '{"continue":true}'