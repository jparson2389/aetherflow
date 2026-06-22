#!/usr/bin/env bash
set -euo pipefail

# Secret-scan gate. Mirrors the CI convention in
# .github/workflows/security.yml: detect-secrets-hook against the shared
# .secrets.baseline with the same exclude pattern. Fails closed — if the
# scanner or its baseline is unavailable, the gate refuses rather than
# coercing an unscanned edit into a clean result.
command -v jq >/dev/null 2>&1 || {
  echo "scan-secrets: jq not available; refusing to continue" >&2
  exit 1
}

INPUT=$(cat)
TOOL_NAME=$(printf '%s' "$INPUT" | jq -er '.tool_name')

if [ "$TOOL_NAME" != "editFiles" ] && [ "$TOOL_NAME" != "createFile" ]; then
  echo '{"continue":true}'
  exit 0
fi

mapfile -t FILES < <(printf '%s' "$INPUT" | jq -r '.tool_input.files[]? // .tool_input.path // empty')

# Only scan files that still exist on disk.
EXISTING=()
for FILE in "${FILES[@]}"; do
  [ -f "$FILE" ] && EXISTING+=("$FILE")
done

if [ ${#EXISTING[@]} -eq 0 ]; then
  echo '{"continue":true}'
  exit 0
fi

# Fail closed: the gate cannot run without its baseline.
if [ ! -f .secrets.baseline ]; then
  echo "scan-secrets: .secrets.baseline not found; refusing to continue" >&2
  exit 1
fi

# detect-secrets-hook exits non-zero when it finds secrets not already
# recorded in the baseline. Surface those to the agent without blocking
# (this is a PostToolUse gate; the edit has already landed).
if ! uv run detect-secrets-hook \
  --baseline .secrets.baseline \
  --exclude-files '(\.env(\.example)?$|agent_manifest\.json$|test_diagnostics_export\.py$|manifest_keys\.json$)' \
  "${EXISTING[@]}" >&2; then
  echo '{"systemMessage":"⚠️ detect-secrets found potential secret(s) not in .secrets.baseline. Review the scan output before committing."}'
  exit 0
fi

echo '{"continue":true}'
