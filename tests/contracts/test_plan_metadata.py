"""Contract test: every non-retired AF-* plan item must carry full verification metadata."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_PLAN_PATH = Path(__file__).parents[2] / 'docs' / 'PLAN.md'

_ITEM_HEADER_RE = re.compile(r'^- \[.\] `(?P<id>AF-[^`]+)`')
_LIFECYCLE_RE = re.compile(r'>\s+\*\*Lifecycle:\*\*\s+`(?P<value>[^`]+)`')
_FEATURE_CLASS_RE = re.compile(r'>\s+\*\*Feature-Class:\*\*\s+`(?P<value>[^`]+)`')
_ENTRY_POINT_RE = re.compile(r'>\s+\*\*Entry-Point:\*\*\s+`(?P<value>[^`]+)`')
_REQUIRED_PROOF_RE = re.compile(
    r'>\s+\*\*Required-Proof-Types:\*\*\s+`(?P<value>[^`]+)`'
)
_EVIDENCE_PACK_RE = re.compile(r'>\s+\*\*Evidence-Pack:\*\*\s+`(?P<value>[^`]+)`')
_APP_TESTABLE_RE = re.compile(r'>\s+\*\*App-Testable:\*\*\s+`(?P<value>[^`]+)`')
_APP_SURFACE_RE = re.compile(r'>\s+\*\*App-Surface:\*\*\s+`(?P<value>[^`]+)`')
_DEVELOPER_ALERT_RE = re.compile(
    r'>\s+\*\*Developer-Alert-Message:\*\*\s+`(?P<value>[^`]+)`'
)
_REQUIRED_FAILURE_MODES_RE = re.compile(
    r'>\s+\*\*Required-Failure-Modes:\*\*\s+`(?P<value>[^`]+)`'
)
_PERFORMANCE_CLAIM_RE = re.compile(
    r'>\s+\*\*Performance-Claim:\*\*\s+`(?P<value>[^`]+)`'
)
_PERFORMANCE_THRESHOLD_RE = re.compile(
    r'>\s+\*\*Performance-Threshold:\*\*\s+`(?P<value>[^`]+)`'
)
_PERFORMANCE_EVIDENCE_TYPE_RE = re.compile(
    r'>\s+\*\*Performance-Evidence-Type:\*\*\s+`(?P<value>[^`]+)`'
)
_PERFORMANCE_EVIDENCE_LOCATION_RE = re.compile(
    r'>\s+\*\*Performance-Evidence-Location:\*\*\s+`(?P<value>[^`]+)`'
)
_AC_LINE_RE = re.compile(r'>\s+-\s+AC\d+:')

_VALID_FEATURE_CLASSES = {'logic', 'service', 'ui', 'boundary', 'workflow'}


def _parse_plan_items(plan_text: str) -> dict[str, dict[str, object]]:
    """Parse all AF-* items from PLAN.md into a dict keyed by item ID.

    Each value is a dict of the item's block lines and extracted metadata.
    """
    items: dict[str, dict[str, object]] = {}
    current_id: str | None = None
    current_lines: list[str] = []

    for line in plan_text.splitlines():
        header_match = _ITEM_HEADER_RE.match(line)
        if header_match:
            if current_id is not None:
                items[current_id] = _extract_metadata(current_lines)
            current_id = header_match.group('id')
            current_lines = [line]
        elif current_id is not None:
            # item block continues until a non-blockquote line that isn't a list item
            if line.startswith('  >') or line.startswith('  - ') or line == '':
                current_lines.append(line)
            else:
                items[current_id] = _extract_metadata(current_lines)
                current_id = None
                current_lines = []

    if current_id is not None:
        items[current_id] = _extract_metadata(current_lines)

    return items


def _extract_metadata(lines: list[str]) -> dict[str, object]:
    """Extract verification metadata fields from an item block's lines."""
    block = '\n'.join(lines)

    lifecycle_match = _LIFECYCLE_RE.search(block)
    feature_class_match = _FEATURE_CLASS_RE.search(block)
    entry_point_match = _ENTRY_POINT_RE.search(block)
    required_proof_match = _REQUIRED_PROOF_RE.search(block)
    evidence_pack_match = _EVIDENCE_PACK_RE.search(block)
    app_testable_match = _APP_TESTABLE_RE.search(block)
    app_surface_match = _APP_SURFACE_RE.search(block)
    developer_alert_match = _DEVELOPER_ALERT_RE.search(block)
    required_failure_modes_match = _REQUIRED_FAILURE_MODES_RE.search(block)
    performance_claim_match = _PERFORMANCE_CLAIM_RE.search(block)
    performance_threshold_match = _PERFORMANCE_THRESHOLD_RE.search(block)
    performance_evidence_type_match = _PERFORMANCE_EVIDENCE_TYPE_RE.search(block)
    performance_evidence_location_match = _PERFORMANCE_EVIDENCE_LOCATION_RE.search(
        block
    )
    has_ac = bool(_AC_LINE_RE.search(block))

    return {
        'lifecycle': lifecycle_match.group('value').strip()
        if lifecycle_match
        else None,
        'feature_class': feature_class_match.group('value').strip()
        if feature_class_match
        else None,
        'entry_point': entry_point_match.group('value').strip()
        if entry_point_match
        else None,
        'required_proof_types': required_proof_match.group('value').strip()
        if required_proof_match
        else None,
        'evidence_pack': evidence_pack_match.group('value').strip()
        if evidence_pack_match
        else None,
        'app_testable': app_testable_match.group('value').strip()
        if app_testable_match
        else None,
        'app_surface': app_surface_match.group('value').strip()
        if app_surface_match
        else None,
        'developer_alert': developer_alert_match.group('value').strip()
        if developer_alert_match
        else None,
        'required_failure_modes': required_failure_modes_match.group('value').strip()
        if required_failure_modes_match
        else None,
        'performance_claim': performance_claim_match.group('value').strip()
        if performance_claim_match
        else None,
        'performance_threshold': performance_threshold_match.group('value').strip()
        if performance_threshold_match
        else None,
        'performance_evidence_type': performance_evidence_type_match.group(
            'value'
        ).strip()
        if performance_evidence_type_match
        else None,
        'performance_evidence_location': performance_evidence_location_match.group(
            'value'
        ).strip()
        if performance_evidence_location_match
        else None,
        'has_acceptance_criteria': has_ac,
    }


@pytest.fixture(scope='module')
def plan_items() -> dict[str, dict[str, object]]:
    """Return all parsed AF-* items from PLAN.md."""
    text = _PLAN_PATH.read_text(encoding='utf-8')
    return _parse_plan_items(text)


@pytest.fixture(scope='module')
def active_items(
    plan_items: dict[str, dict[str, object]],
) -> dict[str, dict[str, object]]:
    """Return only non-retired plan items."""
    return {
        item_id: meta
        for item_id, meta in plan_items.items()
        if meta.get('lifecycle') != 'retired'
    }


def test_retired_item_af_00_01_is_marked(
    plan_items: dict[str, dict[str, object]],
) -> None:
    """AF-00-01 must carry a retired lifecycle marker."""
    assert 'AF-00-01' in plan_items, 'AF-00-01 not found in PLAN.md'
    assert plan_items['AF-00-01']['lifecycle'] == 'retired', (
        'AF-00-01 must have Lifecycle: retired'
    )


def test_retired_items_excluded_from_active(
    active_items: dict[str, dict[str, object]],
) -> None:
    """AF-00-01 must not appear in the active items set."""
    assert 'AF-00-01' not in active_items


def test_all_active_items_have_feature_class(
    active_items: dict[str, dict[str, object]],
) -> None:
    """Every active item must declare a valid Feature-Class."""
    failures: list[str] = []
    for item_id, meta in active_items.items():
        fc = meta.get('feature_class')
        if not fc:
            failures.append(f'{item_id}: missing Feature-Class')
        elif fc not in _VALID_FEATURE_CLASSES:
            failures.append(
                f'{item_id}: invalid Feature-Class "{fc}" (must be one of {sorted(_VALID_FEATURE_CLASSES)})'
            )
    assert not failures, 'Feature-Class issues:\n' + '\n'.join(failures)


def test_all_active_items_have_entry_point(
    active_items: dict[str, dict[str, object]],
) -> None:
    """Every active item must declare a non-empty Entry-Point."""
    failures: list[str] = []
    for item_id, meta in active_items.items():
        ep = meta.get('entry_point')
        if not ep:
            failures.append(f'{item_id}: missing or empty Entry-Point')
    assert not failures, 'Entry-Point issues:\n' + '\n'.join(failures)


def test_all_active_items_have_acceptance_criteria(
    active_items: dict[str, dict[str, object]],
) -> None:
    """Every active item must have at least one AC line (- AC1:)."""
    failures: list[str] = []
    for item_id, meta in active_items.items():
        if not meta.get('has_acceptance_criteria'):
            failures.append(f'{item_id}: no acceptance criteria (- AC1: ...) found')
    assert not failures, 'Acceptance Criteria issues:\n' + '\n'.join(failures)


def test_all_active_items_have_required_proof_types(
    active_items: dict[str, dict[str, object]],
) -> None:
    """Every active item must declare at least one Required-Proof-Types entry."""
    failures: list[str] = []
    for item_id, meta in active_items.items():
        rpt = meta.get('required_proof_types')
        if not rpt:
            failures.append(f'{item_id}: missing Required-Proof-Types')
    assert not failures, 'Required-Proof-Types issues:\n' + '\n'.join(failures)


def test_all_active_items_have_evidence_pack_path(
    active_items: dict[str, dict[str, object]],
) -> None:
    """Every active item must declare an Evidence-Pack path matching docs/evidence/<id>.md."""
    failures: list[str] = []
    for item_id, meta in active_items.items():
        ep = meta.get('evidence_pack')
        if not ep:
            failures.append(f'{item_id}: missing Evidence-Pack')
        else:
            expected = f'docs/evidence/{item_id}.md'
            if ep != expected:
                failures.append(
                    f'{item_id}: Evidence-Pack is "{ep}", expected "{expected}"'
                )
    assert not failures, 'Evidence-Pack issues:\n' + '\n'.join(failures)


def test_all_active_items_have_app_testable(
    active_items: dict[str, dict[str, object]],
) -> None:
    """Every active item must declare App-Testable as true or false."""
    failures: list[str] = []
    for item_id, meta in active_items.items():
        at = meta.get('app_testable')
        if at is None:
            failures.append(f'{item_id}: missing App-Testable')
        elif at.casefold() not in {'true', 'false'}:
            failures.append(
                f'{item_id}: App-Testable must be "true" or "false", got "{at}"'
            )
    assert not failures, 'App-Testable issues:\n' + '\n'.join(failures)


def test_all_active_items_have_required_failure_modes(
    active_items: dict[str, dict[str, object]],
) -> None:
    """Every active item must declare at least one Required-Failure-Modes entry."""
    failures: list[str] = []
    for item_id, meta in active_items.items():
        rfm = meta.get('required_failure_modes')
        if not rfm:
            failures.append(f'{item_id}: missing Required-Failure-Modes')
    assert not failures, 'Required-Failure-Modes issues:\n' + '\n'.join(failures)


def test_app_testable_items_have_app_surface(
    active_items: dict[str, dict[str, object]],
) -> None:
    """Every App-Testable: true item must declare an App-Surface."""
    failures: list[str] = []
    for item_id, meta in active_items.items():
        at = meta.get('app_testable')
        if isinstance(at, str) and at.casefold() == 'true':
            if not meta.get('app_surface'):
                failures.append(
                    f'{item_id}: App-Testable is true but missing App-Surface'
                )
    assert not failures, 'App-Surface issues:\n' + '\n'.join(failures)


def test_app_testable_items_have_developer_alert(
    active_items: dict[str, dict[str, object]],
) -> None:
    """Every App-Testable: true item must declare a Developer-Alert-Message."""
    failures: list[str] = []
    for item_id, meta in active_items.items():
        at = meta.get('app_testable')
        if isinstance(at, str) and at.casefold() == 'true':
            if not meta.get('developer_alert'):
                failures.append(
                    f'{item_id}: App-Testable is true but missing Developer-Alert-Message'
                )
    assert not failures, 'Developer-Alert-Message issues:\n' + '\n'.join(failures)


def test_performance_claim_items_have_threshold_metadata(
    active_items: dict[str, dict[str, object]],
) -> None:
    """Every Performance-Claim: true item must declare Performance-Threshold, Performance-Evidence-Type, and Performance-Evidence-Location."""
    failures: list[str] = []
    for item_id, meta in active_items.items():
        pc = meta.get('performance_claim')
        if isinstance(pc, str) and pc.casefold() == 'true':
            if not meta.get('performance_threshold'):
                failures.append(
                    f'{item_id}: Performance-Claim is true but missing Performance-Threshold'
                )
            if not meta.get('performance_evidence_type'):
                failures.append(
                    f'{item_id}: Performance-Claim is true but missing Performance-Evidence-Type'
                )
            if not meta.get('performance_evidence_location'):
                failures.append(
                    f'{item_id}: Performance-Claim is true but missing Performance-Evidence-Location'
                )
    assert not failures, 'Performance-Claim metadata issues:\n' + '\n'.join(failures)
