#!/usr/bin/env bash
INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name')

if [ "$TOOL_NAME" = "editFiles" ] || [ "$TOOL_NAME" = "createFile" ]; then
  mapfile -t FILES < <(printf '%s' "$INPUT" | jq -r '.tool_input.files[]? // .tool_input.path // empty')
  TESTS_TO_RUN=()

  for FILE in "${FILES[@]}"; do
    # Skip proto files and non-python files
    if echo "$FILE" | grep -qE '(_pb2\.py|_pb2_grpc\.py)$'; then continue; fi
    if [[ "$FILE" != *.py ]]; then continue; fi

    # Tests are organized by type (tests/unit/, tests/integration/, ...), not by
    # mirroring src/aetherflow/. Locate any test_<module>.py under tests/.
    BASENAME=$(basename "$FILE" .py)
    while IFS= read -r MATCH; do
      [ -n "$MATCH" ] && TESTS_TO_RUN+=("$MATCH")
    done < <(find tests -type f -name "test_${BASENAME}.py" 2>/dev/null)
  done

  if [ ${#TESTS_TO_RUN[@]} -gt 0 ]; then
    echo "Running related tests: ${TESTS_TO_RUN[*]}" >&2
    uv run pytest "${TESTS_TO_RUN[@]}" 2>&1 >&2
    if [ $? -ne 0 ]; then
      echo '{"systemMessage":"⚠️ Related tests failed after this edit. Review the test output in the terminal."}'
      exit 0
    fi
  fi
fi

echo '{"continue":true}'