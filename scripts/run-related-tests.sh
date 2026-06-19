#!/usr/bin/env bash
INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name')

if [ "$TOOL_NAME" = "editFiles" ] || [ "$TOOL_NAME" = "createFile" ]; then
  FILES=$(echo "$INPUT" | jq -r '.tool_input.files[]? // .tool_input.path // empty')
  TESTS_TO_RUN=()

  for FILE in $FILES; do
    # Skip proto files and non-python files
    if echo "$FILE" | grep -qE '(_pb2\.py|_pb2_grpc\.py)$'; then continue; fi
    if [[ "$FILE" != *.py ]]; then continue; fi

    # Derive test file path: src/aetherflow/foo/bar.py -> tests/foo/test_bar.py
    BASENAME=$(basename "$FILE" .py)
    POSSIBLE_TEST="tests/$(dirname "$FILE" | sed 's|src/aetherflow/||')/test_${BASENAME}.py"

    if [ -f "$POSSIBLE_TEST" ]; then
      TESTS_TO_RUN+=("$POSSIBLE_TEST")
    fi
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