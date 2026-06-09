"""
Contract tests for PR #28 review surface triage (issue #76).

After force-updating PR #28 from the reconstruction branch, the surviving
review comments are those on files present in the new diff.  This test suite
locks in the fixes applied during triage so they cannot regress.

Surviving comment addressed here:
  - CodeRabbit comment on docs/governance/constraint-inventory.md line 30:
    "Source Ref mis-section: CI-004 through CI-007 are in PRD §2 Guidance,
    not §2 Guidelines."
"""

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_INVENTORY_PATH = PROJECT_ROOT / 'docs' / 'governance' / 'constraint-inventory.md'


def _inventory_rows() -> dict[str, str]:
    """Return {constraint_id: source_ref} for every row in the inventory table."""
    text = _INVENTORY_PATH.read_text(encoding='utf-8')
    rows: dict[str, str] = {}
    for m in re.finditer(r'\|\s*(CI-\d+)\s*\|[^|]+\|\s*([^|]+?)\s*\|', text):
        rows[m.group(1)] = m.group(2).strip()
    return rows


def test_ci_001_to_ci_003_source_ref_is_guidelines() -> None:
    """CI-001 through CI-003 map to PRD §2 Guidelines (platform, stack, IPC)."""
    rows = _inventory_rows()
    for cid in ('CI-001', 'CI-002', 'CI-003'):
        assert rows.get(cid) == '§2 Guidelines', (
            f"{cid} Source Ref should be '§2 Guidelines', got {rows.get(cid)!r}"
        )


def test_ci_004_to_ci_007_source_ref_is_guidance() -> None:
    """CI-004 through CI-007 map to PRD §2 Guidance (TDD, ambiguity, frozen contracts, paths).

    The reviewer correctly identified that these four constraints appear under
    the '### Guidance' heading in docs/PRD.md, not under '### Guidelines'.
    This test prevents the mis-labelling from re-entering the inventory.
    """
    rows = _inventory_rows()
    for cid in ('CI-004', 'CI-005', 'CI-006', 'CI-007'):
        assert rows.get(cid) == '§2 Guidance', (
            f"{cid} Source Ref should be '§2 Guidance' (PRD §2 Guidance section), "
            f"got {rows.get(cid)!r}"
        )
