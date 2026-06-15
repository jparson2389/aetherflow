"""
Contract tests for the native/Python boundary and AF-00-02b verification status.

Covers:
  - AF-00-02b AC2 proof-matrix differentiation (PR comment 3119839623)
  - AF-00-02b verification status on the reconstructed branch (issue #75)

AC2 of AF-00-02b: "Native/Python boundary is enforced."

The native harness (C++ build) proves the boundary at build time (AC1).
These tests prove it from the Python side: no native sources live under
src/, so the boundary is verifiable without MSVC and on every platform.

References
----------
  Evidence pack: docs/evidence/AF-00-02b.md
  Replay slice : https://github.com/jparson2389/aetherflow/issues/75
"""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

_NATIVE_EXTENSIONS = frozenset({'.cpp', '.c', '.cc', '.cxx', '.hpp', '.h'})


def test_af_00_02b_ac2_proof_row_distinct_from_ac1() -> None:
    """AC2 in the AF-00-02b proof matrix must use a different entry point than AC1.

    PR review comment (ID 3119839623) flagged that AC1 and AC2 shared identical
    evidence, making AC2 redundant.  After the fix AC2 must point to the
    Python-side boundary test so a reviewer can tell the two criteria apart.
    """
    text = (PROJECT_ROOT / 'docs' / 'evidence' / 'AF-00-02b.md').read_text(
        encoding='utf-8'
    )
    rows = [
        line.strip() for line in text.splitlines() if line.strip().startswith('| AC')
    ]
    assert len(rows) >= 2, 'Expected at least 2 AC rows in the proof matrix'
    # Entry-point column is index 4 when split on '|' (0=empty, 1=criterion, …)
    ac1_entry = [col.strip() for col in rows[0].split('|')][4]
    ac2_entry = [col.strip() for col in rows[1].split('|')][4]
    assert ac1_entry != ac2_entry, (
        f'AC1 and AC2 share entry point {ac1_entry!r}; '
        'AC2 must reference the Python-side boundary test'
    )


def test_no_native_sources_in_python_source_tree() -> None:
    """No C/C++ files may live under src/.

    AC2 (AF-00-02b): the Native/Python boundary is enforced by keeping
    all native code in include/ and proto/, never in src/.  This check
    runs on every platform, complementing the MSVC-gated harness build.
    """
    src_root = PROJECT_ROOT / 'src'
    native_files = sorted(
        p.relative_to(PROJECT_ROOT).as_posix()
        for p in src_root.rglob('*')
        if p.is_file() and p.suffix.lower() in _NATIVE_EXTENSIONS
    )
    assert not native_files, (
        'Native source files found under src/ — boundary violation:\n'
        + '\n'.join(f'  {f}' for f in native_files)
    )


# ---------------------------------------------------------------------------
# Issue #75 — verification status replay gate
# ---------------------------------------------------------------------------


def test_af_00_02b_status_snapshot_is_present() -> None:
    """status_snapshot.json must exist and track AF-00-02b.

    Replay gate for 8cf77d9: the status snapshot must be present and
    contain an entry for AF-00-02b reflecting the reconstructed branch
    state.  Without MSVC the native build cannot run, so the honest status
    in this environment is 'evidenced' (build-gap), not 'verified'.
    """
    snapshot_path = PROJECT_ROOT / 'logs' / 'verification' / 'status_snapshot.json'
    assert snapshot_path.exists(), 'status_snapshot.json is missing'
    snapshot = json.loads(snapshot_path.read_text(encoding='utf-8'))
    assert 'AF-00-02b' in snapshot.get('items', {}), (
        'AF-00-02b must have an entry in status_snapshot.json'
    )
    # Without MSVC the build-native.ps1 validation cannot run; the item
    # is correctly reported as 'evidenced' (not 'verified') in this env.
    valid_states = {'evidenced', 'verified'}
    status = snapshot['items']['AF-00-02b']
    assert status in valid_states, (
        f'AF-00-02b status must be one of {valid_states}, got {status!r}'
    )


def test_af_00_02b_item_json_present_and_tracked() -> None:
    """AF-00-02b.json must exist and contain required fields.

    Replay gate for 8cf77d9: the per-item artifact must be present on the
    reconstructed branch.  The gap due to missing MSVC is expected and
    noted — the Python-side boundary (AC2) is separately verified by
    test_no_native_sources_in_python_source_tree.
    """
    item_path = PROJECT_ROOT / 'logs' / 'verification' / 'AF-00-02b.json'
    assert item_path.exists(), 'AF-00-02b.json is missing'
    item = json.loads(item_path.read_text(encoding='utf-8'))
    assert item.get('item_id') == 'AF-00-02b'
    assert item.get('evidence_pack') == 'docs/evidence/AF-00-02b.md'
    # Status is 'evidenced' when MSVC is absent; accept either state.
    assert item.get('status') in {'evidenced', 'verified'}, (
        f'Unexpected status {item.get("status")!r} for AF-00-02b.json'
    )
