from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DOC = PROJECT_ROOT / 'docs' / 'verification_standard.md'


def _text() -> str:
    return _DOC.read_text(encoding='utf-8')


def test_document_exists() -> None:
    """docs/verification_standard.md must exist."""
    assert _DOC.exists(), f'Missing: {_DOC}'


def test_definitions_section_covers_implementation() -> None:
    """Definitions section must mention Implementation."""
    text = _text()
    assert '## Definitions' in text, "Missing '## Definitions' section"
    assert 'Implementation' in text, "Missing 'Implementation' definition"


def test_verification_states_section_exists() -> None:
    """Verification States section covers what counts as verification."""
    text = _text()
    assert '## Verification States' in text, "Missing '## Verification States' section"


def test_what_does_not_count_as_proof_section() -> None:
    """What Does Not Count As Proof must list all required disqualifiers."""
    text = _text()
    assert '## What Does Not Count As Proof' in text, (
        "Missing '## What Does Not Count As Proof' section"
    )
    required_phrases = [
        ('file existence', ['file existence']),
        ('line count', ['line count']),
        ('placeholder', ['placeholder']),
        ('import success', ['import success']),
        ('smoke tests or generic smoke', ['smoke tests', 'generic smoke']),
        ('assertion-count', ['assertion-count']),
        ('no exceptions thrown', ['no exceptions thrown']),
        ('LLM or model judgment', ['LLM', 'model']),
    ]
    for label, alternatives in required_phrases:
        assert any(alt in text for alt in alternatives), (
            f"'What Does Not Count As Proof' is missing: {label}"
        )


def test_proof_strength_hierarchy_has_five_levels() -> None:
    """Proof Strength Hierarchy must contain exactly 5 numbered levels."""
    text = _text()
    assert '## Proof Strength Hierarchy' in text, (
        "Missing '## Proof Strength Hierarchy' section"
    )
    # Only count levels 1-5 appearing sequentially within that section
    section_start = text.index('## Proof Strength Hierarchy')
    # Find the next section heading after this one
    next_section = re.search(r'\n## ', text[section_start + 1 :])
    section_text = (
        text[section_start : section_start + 1 + next_section.start()]
        if next_section
        else text[section_start:]
    )
    numbered = re.findall(r'^\s*(\d+)\.', section_text, re.MULTILINE)
    assert len(numbered) == 5, (
        f'Expected 5 levels in Proof Strength Hierarchy, found {len(numbered)}: {numbered}'
    )
    assert numbered == [str(i) for i in range(1, 6)], (
        f'Levels must be numbered 1-5, got: {numbered}'
    )


def test_feature_class_rules_has_all_five_classes() -> None:
    """Feature-Class Rules must cover all 5 feature classes."""
    text = _text()
    assert '## Feature-Class Rules' in text, "Missing '## Feature-Class Rules' section"
    for cls in ('logic', 'service', 'ui', 'boundary', 'workflow'):
        assert cls in text, f'Feature-Class Rules missing class: {cls!r}'


def test_evidence_requirements_section() -> None:
    """Evidence Requirements must list all mandatory proof elements."""
    text = _text()
    assert '## Evidence Requirements' in text, (
        "Missing '## Evidence Requirements' section"
    )
    required = [
        ('acceptance criteria', ['acceptance criteria']),
        ('executable proof', ['executable proof']),
        ('behavioral proof', ['behavioral proof']),
        ('failure or edge proof', ['failure']),
        ('entry point', ['entry point']),
        ('reviewer sign-off or sign-off', ['reviewer sign-off', 'sign-off']),
    ]
    for label, alternatives in required:
        assert any(alt in text for alt in alternatives), (
            f'Evidence Requirements missing: {label}'
        )


def test_human_or_reviewer_signoff_mentioned() -> None:
    """A sign-off requirement (human or reviewer) must be present."""
    text = _text()
    assert 'human sign-off' in text or 'reviewer sign-off' in text, (
        "Missing 'human sign-off' or 'reviewer sign-off' requirement"
    )


def test_developer_app_check_alerts_section() -> None:
    """Developer App-Check Alerts section must cover all alert rules."""
    text = _text()
    assert '## Developer App-Check Alerts' in text, (
        "Missing '## Developer App-Check Alerts' section"
    )
    required = [
        ('startup notice', ['startup notice']),
        ('machine-readable log', ['machine-readable log']),
        ('backfill', ['backfill']),
        ('acknowledge', ['acknowledge']),
    ]
    for label, alternatives in required:
        assert any(alt in text for alt in alternatives), (
            f'Developer App-Check Alerts missing: {label}'
        )
