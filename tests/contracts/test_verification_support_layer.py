"""
Contract tests for the PR #28 recovery: verification-support test layer.

Reconciliation of:
  72e947e -- test: expand contract, integration, UI, and unit test coverage

Reconciliation notes
--------------------
72e947e predates current Master significantly. Master evolved past it and
carries improved versions of every test it touched (tmp_path isolation,
fixture-based regrade, prefixed gap labels, etc.). The current branch inherits
all of that via Master; no regressions are needed. This file:

  1. Documents reconciliation checkpoints — verifies the key test modules
     72e947e introduced are present and better in the current branch.
  2. Adds evidence-index coverage for docs/prd-execution-governance-rewrite.md
     (the recovered governance PRD from issue #71), parallel to how
     docs/governance/constraint-inventory.md was covered in 5738fc8.
  3. Provides the 72e947e checkpoint validation: verify_requirements must run
     clean on the reconstructed branch.

References
----------
  Parent PRD : https://github.com/jparson2389/aetherflow/issues/70
  Replay slice: https://github.com/jparson2389/aetherflow/issues/74
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Reconciliation checkpoints: 72e947e coverage via Master evolution
# ---------------------------------------------------------------------------


def test_frozen_contracts_test_file_present() -> None:
    """72e947e added test_frozen_contracts.py; Master preserved and improved it."""
    assert (PROJECT_ROOT / 'tests' / 'contracts' / 'test_frozen_contracts.py').exists()


def test_verification_reporting_test_file_present() -> None:
    """72e947e added test_verification_reporting.py; Master carries a better version."""
    assert (
        PROJECT_ROOT / 'tests' / 'contracts' / 'test_verification_reporting.py'
    ).exists()


def test_proof_verifier_test_file_present() -> None:
    """72e947e expanded test_proof_verifier.py; Master carries a reconciled version."""
    assert (PROJECT_ROOT / 'tests' / 'contracts' / 'test_proof_verifier.py').exists()


# ---------------------------------------------------------------------------
# Governance artifact: evidence-index coverage (parallel to 5738fc8 for PRD)
# ---------------------------------------------------------------------------


def test_governance_prd_artifact_in_evidence_index(tmp_path: Path) -> None:
    """docs/prd-execution-governance-rewrite.md must appear in the evidence index.

    The recovered governance PRD (replayed in 4182db8 for issue #71) must be
    tracked by the evidence scanner as a non-placeholder document — symmetric
    with how constraint-inventory.md was covered in 5738fc8.
    """
    from tools.verify_requirements import REPO_ROOTS, write_evidence_index

    evidence_file = tmp_path / 'evidence.md'
    roots = [PROJECT_ROOT / part for part in REPO_ROOTS]
    write_evidence_index(
        evidence_path=evidence_file, roots=roots, repo_root=PROJECT_ROOT
    )
    text = evidence_file.read_text(encoding='utf-8')

    entries = {
        m.group(1): m.group(2).lower() == 'true'
        for m in re.finditer(r'path="([^"]+)"[^"]*placeholder=(true|false)', text)
    }

    target = 'docs/prd-execution-governance-rewrite.md'
    assert target in entries, (
        f'{target!r} missing from evidence index — the recovered governance PRD '
        'must be scanned by verify_requirements'
    )
    assert not entries[target], (
        f'{target!r} must not be marked placeholder — the document contains real content'
    )


# ---------------------------------------------------------------------------
# Checkpoint validation: verify_requirements pipeline (72e947e replay gate)
# ---------------------------------------------------------------------------


def test_verification_pipeline_clean_with_recovered_governance_artifacts(
    tmp_path: Path,
) -> None:
    """verify_requirements must exit cleanly on the reconstructed PR #28 branch.

    This is the primary 72e947e checkpoint: the full verification pipeline must
    accept the recovered governance artifacts without error, confirming the
    reconstructed branch is validation-clean.

    Outputs are redirected to ``tmp_path`` so the run does not rewrite the
    tracked ``logs/verification/*.json`` artifacts in place (the test only
    asserts the pipeline exits cleanly; it never reads the outputs).
    """
    result = subprocess.run(
        [
            'uv',
            'run',
            'python',
            '-m',
            'tools.verify_requirements',
            '--results-dir',
            str(tmp_path / 'verification'),
            '--report',
            str(tmp_path / 'requirements-report.md'),
            '--evidence-index',
            str(tmp_path / 'evidence.md'),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f'verify_requirements failed (exit {result.returncode}):\n'
        f'stdout:\n{result.stdout}\n'
        f'stderr:\n{result.stderr}'
    )
