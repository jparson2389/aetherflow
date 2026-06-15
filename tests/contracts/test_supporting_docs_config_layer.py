"""
Contract tests for the PR #28 recovery: supporting docs/config layer.

Verifies the observable outcomes from replaying:
  ad06eb5 -- chore(docs): streamline CLAUDE.md and update .prettierrc settings
  607f4f5 -- chore(docs): update documentation formatting and .gitignore

Conflict resolution documented inline where Master's state diverges from the
original commits (e.g. .gitignore revert in f2156fc).
"""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# ad06eb5 -- .prettierrc markdown settings
# ---------------------------------------------------------------------------


def test_prettierrc_markdown_print_width() -> None:
    """ad06eb5: .prettierrc must set printWidth=1000 for markdown files."""
    prettierrc = PROJECT_ROOT / '.prettierrc'
    assert prettierrc.exists()
    config = json.loads(prettierrc.read_text(encoding='utf-8'))
    md_override = next(
        (o for o in config.get('overrides', []) if o.get('files') == '*.md'),
        None,
    )
    assert md_override is not None, 'No markdown override found in .prettierrc'
    assert md_override['options'].get('printWidth') == 1000


def test_prettierrc_markdown_prose_wrap() -> None:
    """ad06eb5: .prettierrc must set proseWrap=preserve for markdown files."""
    prettierrc = PROJECT_ROOT / '.prettierrc'
    config = json.loads(prettierrc.read_text(encoding='utf-8'))
    md_override = next(
        (o for o in config.get('overrides', []) if o.get('files') == '*.md'),
        None,
    )
    assert md_override is not None
    assert md_override['options'].get('proseWrap') == 'preserve'


def test_prettierrc_markdown_tab_width() -> None:
    """ad06eb5: .prettierrc markdown override must use tabWidth=2."""
    prettierrc = PROJECT_ROOT / '.prettierrc'
    config = json.loads(prettierrc.read_text(encoding='utf-8'))
    md_override = next(
        (o for o in config.get('overrides', []) if o.get('files') == '*.md'),
        None,
    )
    assert md_override is not None
    assert md_override['options'].get('tabWidth') == 2


# ---------------------------------------------------------------------------
# ad06eb5 -- CLAUDE.md condensed structure
# ---------------------------------------------------------------------------


def test_claude_md_instruction_priority_section() -> None:
    """ad06eb5: CLAUDE.md must have Instruction Priority section with AGENTS.md reference."""
    text = (PROJECT_ROOT / 'CLAUDE.md').read_text(encoding='utf-8')
    assert '## Instruction Priority' in text
    assert '`AGENTS.md`' in text
    assert '`.claude/rules/*.md`' in text


def test_claude_md_repository_baseline_section() -> None:
    """ad06eb5: CLAUDE.md must reference AGENTS.md as the canonical source."""
    text = (PROJECT_ROOT / 'CLAUDE.md').read_text(encoding='utf-8')
    assert '## Repository Baseline' in text
    assert 'Follow `AGENTS.md` as the canonical source' in text


def test_claude_md_environment_notes_section() -> None:
    """ad06eb5: CLAUDE.md must have environment notes with Windows/PowerShell reference."""
    text = (PROJECT_ROOT / 'CLAUDE.md').read_text(encoding='utf-8')
    assert '## Environment Notes' in text
    assert 'Windows' in text


def test_claude_md_claude_specific_expectations_section() -> None:
    """ad06eb5: CLAUDE.md must retain Claude-Specific Expectations section."""
    text = (PROJECT_ROOT / 'CLAUDE.md').read_text(encoding='utf-8')
    assert '## Claude-Specific Expectations' in text


# ---------------------------------------------------------------------------
# 607f4f5 -- tasks/tasks-af-03-02-remediation.md
# ---------------------------------------------------------------------------


def test_af03_remediation_tasks_file_exists() -> None:
    """607f4f5: tasks/tasks-af-03-02-remediation.md must exist on the recovery branch."""
    tasks_file = PROJECT_ROOT / 'tasks' / 'tasks-af-03-02-remediation.md'
    assert tasks_file.exists(), (
        'AF-03-02 remediation task file missing from recovery branch'
    )


def test_af03_remediation_tasks_file_has_relevant_files() -> None:
    """607f4f5: tasks file must list the relevant source files for AF-03-02."""
    text = (PROJECT_ROOT / 'tasks' / 'tasks-af-03-02-remediation.md').read_text(
        encoding='utf-8'
    )
    assert '## Relevant Files' in text
    assert 'RenderModePanelModel' in text
    assert 'render_mode_panel.py' in text


def test_af03_remediation_tasks_file_has_task_structure() -> None:
    """607f4f5: tasks file must contain the remediation task checklist."""
    text = (PROJECT_ROOT / 'tasks' / 'tasks-af-03-02-remediation.md').read_text(
        encoding='utf-8'
    )
    assert '## Tasks' in text
    assert 'AF-03-02' in text


# ---------------------------------------------------------------------------
# 607f4f5 -- documentation prettier-ignore table formatting
# ---------------------------------------------------------------------------


def test_security_md_prettier_ignore_for_tables() -> None:
    """607f4f5: SECURITY.md tables must be wrapped with prettier-ignore comments."""
    text = (PROJECT_ROOT / 'SECURITY.md').read_text(encoding='utf-8')
    assert '<!-- prettier-ignore-start -->' in text
    assert '<!-- prettier-ignore-end -->' in text


def test_plan_md_prettier_ignore_for_tables() -> None:
    """607f4f5: docs/PLAN.md tables must be wrapped with prettier-ignore comments."""
    text = (PROJECT_ROOT / 'docs' / 'PLAN.md').read_text(encoding='utf-8')
    assert '<!-- prettier-ignore-start -->' in text
    assert '<!-- prettier-ignore-end -->' in text


def test_prd_md_prettier_ignore_for_tables() -> None:
    """607f4f5: docs/PRD.md tables must be wrapped with prettier-ignore comments."""
    text = (PROJECT_ROOT / 'docs' / 'PRD.md').read_text(encoding='utf-8')
    assert '<!-- prettier-ignore-start -->' in text
    assert '<!-- prettier-ignore-end -->' in text


# ---------------------------------------------------------------------------
# Conflict resolution: 607f4f5 vs Master (f2156fc revert)
# ---------------------------------------------------------------------------


def test_gitignore_does_not_exclude_wrap_markdown_tables() -> None:
    """
    Conflict resolution for 607f4f5 vs Master.

    607f4f5 added tools/wrap_markdown_tables.py to .gitignore, but Master
    subsequently un-ignored it in f2156fc so the script is tracked. Per the
    recovery PRD authority order (issue/PRD intent first, then Master as
    evidence), the correct resolution is to keep the script tracked: it is a
    legitimate tool that should be version-controlled.
    """
    text = (PROJECT_ROOT / '.gitignore').read_text(encoding='utf-8')
    assert 'tools/wrap_markdown_tables.py' not in text, (
        'wrap_markdown_tables.py must not appear in .gitignore; '
        'Master correctly un-ignored it after 607f4f5 landed'
    )
