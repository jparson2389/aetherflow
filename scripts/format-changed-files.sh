#!/usr/bin/env bash
# format-changed-files.sh
# Runs after the agent edits or creates a file.
# - Python: Ruff format + lint fix (skips proto-generated files)
# - Markdown: Prettier + markdownlint-cli2
# - JSON, JSONC, YAML, YML: Prettier
# Respects .prettierignore and .markdownlintignore automatically.

set -euo pipefail

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name')

# Only act on file edit/create tools
if [ "$TOOL_NAME" != "editFiles" ] && [ "$TOOL_NAME" != "createFile" ]; then
  echo '{"continue":true}'
  exit 0
fi

mapfile -t FILES < <(printf '%s' "$INPUT" | jq -r '.tool_input.files[]? // .tool_input.path // empty')

PYTHON_FILES=()
MARKDOWN_FILES=()
PRETTIER_FILES=()

for FILE in "${FILES[@]}"; do
  # Skip if file doesn't exist
  [ -f "$FILE" ] || continue

  # Skip proto-generated files regardless of extension
  if echo "$FILE" | grep -qE '(_pb2\.py|_pb2_grpc\.py)$'; then
    echo "Skipping proto-generated file: $FILE" >&2
    continue
  fi

  case "$FILE" in
    *.py)
      PYTHON_FILES+=("$FILE")
      ;;
    *.md)
      MARKDOWN_FILES+=("$FILE")
      ;;
    *.json|*.jsonc|*.yaml|*.yml)
      PRETTIER_FILES+=("$FILE")
      ;;
  esac
done

# --- Python: Ruff ---
if [ ${#PYTHON_FILES[@]} -gt 0 ]; then
  for FILE in "${PYTHON_FILES[@]}"; do
    echo "Ruff: formatting $FILE" >&2
    uv run ruff format "$FILE" >&2
    uv run ruff check --fix "$FILE" >&2
  done
fi

# --- Markdown: Prettier then markdownlint-cli2 ---
if [ ${#MARKDOWN_FILES[@]} -gt 0 ]; then
  for FILE in "${MARKDOWN_FILES[@]}"; do
    echo "Prettier: formatting $FILE" >&2
    npx prettier --write "$FILE" >&2

    echo "markdownlint: linting $FILE" >&2
    # markdownlint-cli2 exits non-zero on lint errors — capture and warn, don't block
    if ! npx markdownlint-cli2 "$FILE" >&2; then
      LINT_WARNINGS="${LINT_WARNINGS:-}\\n- $FILE"
    fi
  done
fi

# --- JSON / JSONC / YAML: Prettier only ---
if [ ${#PRETTIER_FILES[@]} -gt 0 ]; then
  for FILE in "${PRETTIER_FILES[@]}"; do
    echo "Prettier: formatting $FILE" >&2
    npx prettier --write "$FILE" >&2
  done
fi

# Surface markdownlint warnings to the agent without blocking
if [ -n "${LINT_WARNINGS:-}" ]; then
  echo "{\"systemMessage\":\"⚠️ markdownlint found issues in the following files — review them:$LINT_WARNINGS\"}"
  exit 0
fi

echo '{"continue":true}'