#!/bin/bash
BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
PYTHON=$(uv run python --version 2>/dev/null || echo "unknown")
UV=$(uv --version 2>/dev/null || echo "unknown")

cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "Project: aetherflow v0.1.0 | Branch: $BRANCH | $PYTHON | $UV | Linter: Ruff | Tests: pytest (tests/) | Proto files in src/aetherflow/proto are auto-generated — never edit directly. Source roots: src/, tools/. Use uv run for all Python commands."
  }
}
EOF