"""
Contract tests for the native/Python boundary and AF-00-02b verification status.

Covers:
  - AF-00-02b AC2 proof-matrix differentiation (PR comment 3119839623)
  - Python-side native source tree enforcement (AC2 behavioral proof)

AC2 of AF-00-02b: "Native/Python boundary is enforced."

The native harness (C++ build) proves the boundary at build time (AC1).
These tests prove it from the Python side: no native sources live under
src/, so the boundary is verifiable without MSVC and on every platform.

References
----------
  Evidence pack: docs/evidence/AF-00-02b.md
  Artifact policy: docs/governance/artifact-storage-policy.md
"""

from __future__ import annotations

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
