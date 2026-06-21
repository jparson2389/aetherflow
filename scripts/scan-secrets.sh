#!/usr/bin/env bash
set -euo pipefail

# Fail closed: a secret-scan gate must not coerce scanner/parser failures into a
# clean result. Missing jq exits non-zero rather than allowing unscanned edits.
command -v jq >/dev/null 2>&1 || {
  echo "scan-secrets: jq not available; refusing to continue" >&2
  exit 1
}

INPUT=$(cat)
TOOL_NAME=$(printf '%s' "$INPUT" | jq -er '.tool_name')

if [ "$TOOL_NAME" = "editFiles" ] || [ "$TOOL_NAME" = "createFile" ]; then
  mapfile -t FILES < <(printf '%s' "$INPUT" | jq -r '.tool_input.files[]? // .tool_input.path // empty')

  for FILE in "${FILES[@]}"; do
    if [[ "$FILE" == *.py ]] || [[ "$FILE" == *.env ]] || [[ "$FILE" == *.yaml ]] || [[ "$FILE" == *.yml ]]; then
      if [ -f "$FILE" ]; then
        # Fail closed: a scanner crash must reject the edit, not pass as clean.
        if ! RESULT=$(uv run detect-secrets scan --all-files "$FILE" 2>/dev/null); then
          echo '{"systemMessage":"❌ Secret scan failed; refusing to continue."}'
          exit 1
        fi
        # Check if any secrets were found (results array non-empty)
        COUNT=$(printf '%s' "$RESULT" | jq -er '[.results | to_entries[].value[]] | length')
        if [ "$COUNT" -gt "0" ]; then
          MSG="detect-secrets found $COUNT potential secret(s) in $FILE. Review before committing."
          echo "{\"systemMessage\": \"⚠️ $MSG\"}"
          exit 0
        fi
      fi
    fi
  done
fi

echo '{"continue":true}'
