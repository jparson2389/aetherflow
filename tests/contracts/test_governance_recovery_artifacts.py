from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_recovery_branch_contains_execution_governance_prd_artifact() -> None:
    artifact_path = PROJECT_ROOT / 'docs' / 'prd-execution-governance-rewrite.md'

    assert artifact_path.exists()

    artifact_text = artifact_path.read_text(encoding='utf-8')

    assert artifact_text.startswith('# PRD: Execution Governance Rewrite')
    assert '## Problem Statement' in artifact_text
    assert '## Solution' in artifact_text
    assert '## User Stories' in artifact_text
    assert '## Implementation Decisions' in artifact_text
    assert '## Testing Decisions' in artifact_text
    assert '## Out of Scope' in artifact_text
    assert 'phase-blocking system built around four canonical artifact types' in artifact_text
    assert 'foundational constraint ledger' in artifact_text


def test_recovery_branch_contains_constraint_inventory_artifact() -> None:
    artifact_path = PROJECT_ROOT / 'docs' / 'governance' / 'constraint-inventory.md'

    assert artifact_path.exists()

    artifact_text = artifact_path.read_text(encoding='utf-8')

    assert artifact_text.startswith('# Constraint Inventory')
    assert '## Source Set' in artifact_text
    assert '## Inventory' in artifact_text
    assert '## Classification Key' in artifact_text
    assert '`docs/PRD.md`' in artifact_text
    assert '`docs/PLAN.md`' in artifact_text
    assert '`AGENTS.md`' in artifact_text
    assert '`docs/verification_standard.md`' in artifact_text
    assert '`docs/verify-requirements-pipeline.md`' in artifact_text
    assert '`CLAUDE.md`' in artifact_text
    assert '| CI-001 |' in artifact_text
    assert '| CI-050 |' in artifact_text
