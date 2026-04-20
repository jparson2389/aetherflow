"""Contract test: every non-retired AF-* plan item must have a valid evidence pack."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# All non-retired AF-* item IDs that must have evidence packs.
ALL_ITEM_IDS = [
    'AF-00-02a',
    'AF-00-02b',
    'AF-00-03',
    'AF-00-04',
    'AF-00-05',
    'AF-01-01',
    'AF-01-02',
    'AF-02-01',
    'AF-02-02',
    'AF-03-01',
    'AF-03-02',
    'AF-04-01',
    'AF-04-02',
    'AF-05-01',
    'AF-05-02',
]

EVIDENCE_DIR = Path(__file__).resolve().parents[2] / 'docs' / 'evidence'

_REVIEWER_STATUS_RE = re.compile(r'^- Reviewer Status:\s*\S+')
_AC_BULLET_RE = re.compile(r'^- AC\d+:')
_PROOF_ROW_RE = re.compile(r'^\| AC\d+')
_SIGN_OFF_STATUS_RE = re.compile(r'^- Status:\s*\S+')


def _assert_evidence_pack_valid(item_id: str) -> None:
    """Assert that the evidence pack for *item_id* exists and passes structural checks.

    Args:
        item_id: Stable plan-item identifier such as ``AF-02-01``.

    """
    pack_path = EVIDENCE_DIR / f'{item_id}.md'

    # File must exist.
    assert pack_path.exists(), f'Missing evidence pack: {pack_path.as_posix()}'

    text = pack_path.read_text(encoding='utf-8')
    lines = [line.rstrip() for line in text.splitlines()]

    # Must contain a Reviewer Status metadata line.
    has_reviewer_status = any(_REVIEWER_STATUS_RE.match(ln) for ln in lines)
    assert has_reviewer_status, f"{item_id}: missing '- Reviewer Status:' metadata line"

    # Must have an ## Acceptance Criteria section with at least one - AC bullet.
    assert '## Acceptance Criteria' in lines, (
        f"{item_id}: missing '## Acceptance Criteria' section"
    )
    has_ac_bullet = any(_AC_BULLET_RE.match(ln) for ln in lines)
    assert has_ac_bullet, (
        f"{item_id}: '## Acceptance Criteria' section has no '- AC' bullets"
    )

    # Must have a ## Proof Matrix section with at least one | AC row.
    assert '## Proof Matrix' in lines, f"{item_id}: missing '## Proof Matrix' section"
    has_proof_row = any(_PROOF_ROW_RE.match(ln) for ln in lines)
    assert has_proof_row, (
        f"{item_id}: '## Proof Matrix' section has no '| AC' data rows"
    )

    # Must have a ## Sign-Off section with a - Status: line.
    assert '## Sign-Off' in lines, f"{item_id}: missing '## Sign-Off' section"
    has_sign_off_status = any(_SIGN_OFF_STATUS_RE.match(ln) for ln in lines)
    assert has_sign_off_status, (
        f"{item_id}: '## Sign-Off' section has no '- Status:' line"
    )


@pytest.mark.parametrize('item_id', ALL_ITEM_IDS)
def test_evidence_pack_exists_and_is_valid(item_id: str) -> None:
    """Each non-retired plan item must have a structurally valid evidence pack.

    Args:
        item_id: Plan-item identifier under test.

    """
    _assert_evidence_pack_valid(item_id)
