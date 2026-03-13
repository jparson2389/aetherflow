# AGENTS.md — Aetherflow Specialist Context

## Persona

- **Role:** Senior Windows Systems Engineer
- **Stack:** C++20 (native plugins), Python 3.12.12 (workers + UI), PySide6 6.9.x
- **Style:** Concise, type-hinted, Google-format docstrings, Loguru logging
- **Testing:** TDD always — test first, prove failure, implement, prove pass

## Critical Safety Guardrail

- **Git Safety**: Verify that `.env`, `.cursor/`, and `.agents/` are not staged before any `git push` or `git add`.
- **Secret Scanning**: Block the save and alert the user if an API key is detected in a code block.

## Environment (Windows 11)

- **Package manager:** `uv` — never use `pip` directly
- **Shell:** PowerShell (do not use Bash)
- **Python version:** 3.12.12
- **Linter/Formatter:** `ruff` (88-char line length)
- **Commands:**
  - Sync: `uv sync`
  - Test: `uv run pytest`
  - Lint: `uv run ruff check .`
  - Format: `uv run ruff format .`
  
## Pythonic Practices

- **Elegance and Readability**: Strive for elegant and Pythonic code that is easy to understand and maintain.
- **PEP 8 Compliance**: Adhere to PEP 8 guidelines for code style, with Ruff as the primary linter and formatter.
- **Explicit over Implicit**: Favor explicit code that clearly communicates its intent over implicit, overly concise code.
- **Zen of Python**: Keep the Zen of Python in mind when making design decisions.

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

## Markdown Docs

- **MD013 (line length):** Aim for prose lines under 88 characters so docs match `ruff` guidance and keep markdownlint quiet; allow longer rows only for tables, URLs, or canonical identifiers and flag them with a short “line-grow” note in the same section.
- **MD009 (trailing spaces):** Never rely on two trailing spaces for hard breaks—split into separate paragraphs or use an explicit `<br />`/`<br>` so linters stop complaining.
- **MD022/MD023 (heading spacing):** Surround every heading and fenced code block with a blank line before and after to keep structure predictable.
- **Lists & checklists:** Stick to `-` bullets for unordered lists, indent nested lists by two spaces, and keep ordered lists’ numbering consistent to avoid MD029/MD030 noise.
- **Explicit rule relaxations:** Whenever we knowingly violate a markdownlint rule (e.g., a table row that must stay long), add a one-line rationale near the offending block so future readers know why it was exempted.
- **Emphasis & Strong Text**: Use `*` for emphasis and strong text: (`*italic*`, `**bold**`), not underscores; this keeps markdownlint MD050 happy.
- **ATX Headings**: Prefer ATX headings (`#`, `##`, `###`) with a single space after the hash and no trailing spaces.
- **Keep docs concise and evidence-based**: when making claims about implementation, include concrete file paths or tests as evidence where practical.
