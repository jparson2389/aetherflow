import re
from pathlib import Path

from tools.verify_requirements import REPO_ROOTS, write_evidence_index

PROJECT_ROOT = Path(__file__).resolve().parents[2]

_CANONICAL_INVENTORY_PATH = 'docs/governance/constraint-inventory.md'
_STALE_INVENTORY_PATH = 'docs/governance/foundational-constraint-inventory.md'


def _fresh_evidence_paths(tmp_path: Path) -> set[str]:
    """Generate a fresh evidence index and return the set of scanned paths."""
    evidence_file = tmp_path / 'evidence.md'
    roots = [PROJECT_ROOT / part for part in REPO_ROOTS]
    write_evidence_index(evidence_path=evidence_file, roots=roots, repo_root=PROJECT_ROOT)
    text = evidence_file.read_text(encoding='utf-8')
    return {m.group(1) for m in re.finditer(r'path="([^"]+)"', text)}


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
    assert '| CI-001 |' in artifact_text
    assert '| CI-050 |' in artifact_text


def test_canonical_inventory_path_in_evidence_index(tmp_path: Path) -> None:
    """The live evidence index must track the canonical artifact, not the stale name.

    Prevents recurrence of the untracked-only document/CI mismatch: the recovered
    branch chose docs/governance/constraint-inventory.md as the canonical landing
    slice; this contract ensures the evidence scanner agrees and the old name
    (foundational-constraint-inventory.md) is absent.
    """
    paths = _fresh_evidence_paths(tmp_path)

    assert _CANONICAL_INVENTORY_PATH in paths, (
        f'Canonical inventory artifact {_CANONICAL_INVENTORY_PATH!r} '
        'is missing from the evidence index'
    )
    assert _STALE_INVENTORY_PATH not in paths, (
        f'Stale inventory name {_STALE_INVENTORY_PATH!r} must not appear '
        'in the evidence index; the canonical artifact is '
        f'{_CANONICAL_INVENTORY_PATH!r}'
    )
