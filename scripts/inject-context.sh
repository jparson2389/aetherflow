#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
BRANCH=$(git -C "$REPO_ROOT" branch --show-current 2>/dev/null || echo "unknown")
PYTHON=$(uv run python --version 2>/dev/null || echo "unknown")
UV=$(uv --version 2>/dev/null || echo "unknown")

HEADER="Project: aetherflow v0.1.0 | Branch: $BRANCH | $PYTHON | $UV"

AGENTS_FILE="$REPO_ROOT/AGENTS.md"
if [[ -f "$AGENTS_FILE" ]]; then
    AGENTS_BODY="$(cat "$AGENTS_FILE")"
else
    AGENTS_BODY="(AGENTS.md missing at $AGENTS_FILE)"
fi

ADDITIONAL_CONTEXT=$(printf '%s\n\n--- AGENTS.md (canonical repo standards) ---\n\n%s' \
    "$HEADER" "$AGENTS_BODY")

jq -n --arg ctx "$ADDITIONAL_CONTEXT" '{
  hookSpecificOutput: {
    hookEventName: "SessionStart",
    additionalContext: $ctx
  }
}'
