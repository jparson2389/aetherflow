# CLAUDE.md

This file provides Claude Code guidance for this repository.

## Instruction Priority

Apply instructions in this order:

1. Direct user request
2. `AGENTS.md`
3. `.claude/rules/*.md`

## Repository Baseline

Follow `AGENTS.md` as the canonical source for:

- architecture boundaries
- repo structure
- coding standards
- testing and validation
- dependency restrictions
- generated-file handling

## Claude-Specific Expectations

- Make the smallest safe change that satisfies the task
- Preserve unrelated user changes
- Keep diffs reviewable
- Do not restate success without running verification
- Prefer targeted verification before broad verification

## Environment Notes

- Primary dev platform: Windows / PowerShell 7
- Prefer `uv run python -m tools.*` entry points where available
- Native C++ build steps must run in a Windows-capable environment
