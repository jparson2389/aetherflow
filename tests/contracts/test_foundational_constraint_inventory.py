from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOC = PROJECT_ROOT / 'docs' / 'governance' / 'foundational-constraint-inventory.md'


def _text() -> str:
    return DOC.read_text(encoding='utf-8')


def test_document_exists() -> None:
    assert DOC.exists(), f'Missing: {DOC}'


def test_inventory_has_required_sections() -> None:
    text = _text()
    required_sections = [
        '# Foundational Constraint Inventory',
        '## Scope',
        '## Source Set',
        '## Normalized Inventory',
        '## Notes For Follow-On Audit',
    ]
    for section in required_sections:
        assert section in text, f'Missing section: {section}'


def test_inventory_covers_required_governing_sources() -> None:
    text = _text()
    required_sources = [
        'AGENTS.md',
        'docs/PLAN.md',
        'docs/PRD.md',
        'docs/requirements-report.md',
        'docs/verification_standard.md',
        'docs/verify-requirements-pipeline.md',
        'tests/contracts/test_execution_contracts.py',
        'tests/contracts/test_plan_completion_policy.py',
        'tests/contracts/test_prd_execution_readiness.py',
    ]
    for source in required_sources:
        assert source in text, f'Missing governing source: {source}'


def test_inventory_table_has_required_columns() -> None:
    text = _text()
    pattern = re.compile(
        r'^\|\s*ID\s*\|\s*Source\s*\|\s*Source Ref\s*\|\s*Constraint Summary\s*\|'
        r'\s*Constraint Type\s*\|\s*Initial Audit Candidate\s*\|$',
        re.MULTILINE,
    )
    assert pattern.search(text), 'Normalized inventory table header is missing'


def test_inventory_has_nontrivial_number_of_entries() -> None:
    text = _text()
    row_pattern = re.compile(r'^\| FCI-\d+ \|', re.MULTILINE)
    rows = row_pattern.findall(text)
    assert len(rows) >= 12, f'Expected at least 12 inventory rows, found {len(rows)}'


def test_inventory_uses_initial_classification_candidates() -> None:
    text = _text()
    required_candidates = [
        'likely-enforced',
        'likely-doc-only',
        'needs-audit',
    ]
    for candidate in required_candidates:
        assert candidate in text, f'Missing classification candidate: {candidate}'
