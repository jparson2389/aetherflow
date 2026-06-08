"""
Contract tests for artifact storage gitignore policy.

Enforces docs/governance/artifact-storage-policy.md Tier 2 rules: generated
verification JSON must stay out of git without negation exceptions.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _gitignore_lines() -> list[str]:
    """Return non-empty, non-comment lines from the repo .gitignore."""
    text = (PROJECT_ROOT / '.gitignore').read_text(encoding='utf-8')
    return [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith('#')
    ]


def test_gitignore_ignores_verification_json_exactly_once() -> None:
    """logs/verification/*.json must appear exactly once in .gitignore."""
    matches = [
        line for line in _gitignore_lines() if line == 'logs/verification/*.json'
    ]
    assert len(matches) == 1, (
        'Expected logs/verification/*.json exactly once in .gitignore, '
        f'found {len(matches)}: {matches}'
    )


def test_gitignore_does_not_unignore_verification_directory() -> None:
    """Negation !logs/verification/ must not appear — it re-enables git tracking."""
    text = (PROJECT_ROOT / '.gitignore').read_text(encoding='utf-8')
    assert '!logs/verification/' not in text, (
        '!logs/verification/ negates the ignore policy and allows JSON churn'
    )


def test_gitignore_ndjson_and_prompt_patterns_on_separate_lines() -> None:
    """logs/*.ndjson and logs/prompt_*.txt must be separate valid patterns."""
    lines = _gitignore_lines()
    assert 'logs/*.ndjson' in lines
    assert 'logs/prompt_*.txt' in lines
    merged = [
        line
        for line in lines
        if 'logs/*.ndjson' in line and 'logs/prompt_*.txt' in line
    ]
    assert not merged, (
        f'Merged ndjson/prompt pattern is invalid gitignore syntax: {merged}'
    )


def test_gitignore_does_not_reference_phantom_script_paths() -> None:
    """Phantom script paths that do not exist must not appear in .gitignore."""
    text = (PROJECT_ROOT / '.gitignore').read_text(encoding='utf-8')
    phantom_patterns = (
        'scripts/with-env.sh',
        'scripts/with-env.ps1',
        'scripts/dev-shell.sh',
        'scripts/dev-shell.ps1',
    )
    for pattern in phantom_patterns:
        assert pattern not in text, (
            f'Phantom path {pattern!r} must not be in .gitignore'
        )
