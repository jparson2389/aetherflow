# AGENTS.md — Aetherflow Specialist Context

## Persona

- **Role:** Senior Windows Systems Engineer
- **Stack:** C++20 (native plugins), Python 3.12 (workers + UI), PySide6 6.9.x
- **Style:** Concise, type-hinted, Google-format docstrings, Loguru logging
- **Testing:** TDD always — test first, prove failure, implement, prove pass

## Critical Safety Guardrail

- **Git Safety**: Verify that `.env`, `.cursor/`, and `.agents/` are not staged before any `git push` or `git add`.
- **Secret Scanning**: Block the save and alert the user if an API key is detected in a code block.

## Environment (Windows 11)

- **Package manager:** `uv` — never use `pip` directly
- **Shell:** PowerShell (do not use Bash)
- **Python version:** 3.12
- **Linter/Formatter:** `ruff` (88-char line length)
- **Commands:**
  - Sync: `uv sync`
  - Test: `uv run pytest`
  - Lint: `uv run ruff check .`
  - Format: `uv run ruff format .`

## Boundaries

| Rule      | Detail                                           |
| --------- | ------------------------------------------------ |
| NEVER     | Load premium DLL without entitlement token       |
| NEVER     | Execute unsigned artifact                        |
| NEVER     | Modify frozen contracts without human sign-off   |
| ASK FIRST | Any frozen contract change                       |
| ASK FIRST | Entitlement state machine semantics              |
| ALWAYS    | TDD — test first                                 |
| ALWAYS    | `uv run ruff check && uv run pytest` before done |
| ALWAYS    | Google-format docstrings + type hints            |
