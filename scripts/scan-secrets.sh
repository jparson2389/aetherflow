#!/bin/bash
INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name')

if [ "$TOOL_NAME" = "editFiles" ] || [ "$TOOL_NAME" = "createFile" ]; then
  FILES=$(echo "$INPUT" | jq -r '.tool_input.files[]? // .tool_input.path // empty')

  for FILE in $FILES; do
    if [[ "$FILE" == *.py ]] || [[ "$FILE" == *.env ]] || [[ "$FILE" == *.yaml ]] || [[ "$FILE" == *.yml ]]; then
      if [ -f "$FILE" ]; then
        RESULT=$(uv run detect-secrets scan "$FILE" 2>/dev/null)
        # Check if any secrets were found (results array non-empty)
        COUNT=$(echo "$RESULT" | jq '[.results | to_entries[].value[]] | length' 2>/dev/null || echo "0")
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