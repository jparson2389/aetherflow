"""End-to-end fixture for the full verification chain."""

from __future__ import annotations

import json
from pathlib import Path

from src.aetherflow.core.developer_app_checks import (
    PendingAppCheckStore,
)
from src.aetherflow.core.verification_report import (
    PlanItem,
    VerificationResult,
    evaluate_plan_item,
    write_results,
)
from src.aetherflow.ui.shell import ShellModel


def _write_evidence_pack(path: Path, *, reviewer_status: str) -> None:
    """Write a minimal evidence pack to path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '\n'.join([
            '# AF-TEST-01 Evidence Pack',
            '',
            f'- Reviewer Status: {reviewer_status}',
            '- Reviewer: qa.lead',
            '- Reviewed At: 2026-03-19T12:00:00Z',
            '- App-Testable: yes',
            '- App Surface: test-surface',
            '- Developer Alert: Test item verified, check test-surface.',
            '',
            '## Acceptance Criteria',
            '',
            '- AC1: Synthetic test item is reachable from its intended entry point.',
            '',
            '## Proof Matrix',
            '',
            '| Criterion | Proof Type | Evidence | Entry Point | Failure Coverage |',
            '| --- | --- | --- | --- | --- |',
            '| AC1 | integration | tests/unit/test_example.py | test-entry-point | invalid input rejected |',
            '',
            '## Sign-Off',
            '',
            f'- Status: {reviewer_status}',
            '- Notes: Test sign-off.',
            '',
        ]),
        encoding='utf-8',
    )


def test_full_verification_chain(tmp_path: Path) -> None:
    """Exercise the complete verification chain from plan item to acknowledged alert."""
    # ── Step 1: Plan item metadata ────────────────────────────────────────
    item = PlanItem(
        item_id='AF-TEST-01',
        title='Synthetic test item',
        targets=[],
        validations=['uv run pytest tests/unit/test_example.py'],
        evidence_pack=Path('evidence/AF-TEST-01.md'),
        feature_class='service',
        entry_point='test-entry-point',
        required_proofs=['integration'],
        failure_modes=['invalid input rejected'],
    )

    # ── Step 2: Evidence pack created ─────────────────────────────────────
    evidence_path = tmp_path / 'evidence' / 'AF-TEST-01.md'
    _write_evidence_pack(evidence_path, reviewer_status='pending')

    # ── Step 3: Validation stub passes ────────────────────────────────────
    # Step 4: Sign-off applied — rewrite pack with approved status
    _write_evidence_pack(evidence_path, reviewer_status='approved')

    # ── Step 5: evaluate_plan_item promotes to verified ───────────────────
    result = evaluate_plan_item(
        repo_root=tmp_path,
        item=item,
        validation_runner=lambda _repo_root, _command: True,
    )
    assert result.status == 'verified', f'Expected verified, got {result.status}: {result.gaps}'
    assert result.app_testable is True
    assert result.app_surface == 'test-surface'
    assert result.developer_alert is not None

    # ── Step 6: Write JSON verification artifact ──────────────────────────
    logs_dir = tmp_path / 'logs' / 'verification'
    logs_dir.mkdir(parents=True, exist_ok=True)
    report_path = tmp_path / 'docs' / 'requirements-report.md'
    report_path.parent.mkdir(parents=True, exist_ok=True)
    write_results(
        report_path=report_path,
        results_dir=logs_dir,
        results=[result],
    )
    json_path = logs_dir / 'AF-TEST-01.json'
    assert json_path.exists(), 'Verification JSON was not written'
    payload = json.loads(json_path.read_text(encoding='utf-8'))
    assert payload['status'] == 'verified'
    assert payload['item_id'] == 'AF-TEST-01'

    # ── Step 7: Pending alert created ─────────────────────────────────────
    store = PendingAppCheckStore(
        pending_path=logs_dir / 'pending_app_checks.json',
        snapshot_path=logs_dir / 'status_snapshot.json',
    )
    # First sync: baselines (no alert)
    store.sync_results([
        VerificationResult(
            item_id='AF-TEST-01',
            title='Synthetic test item',
            status='coded',
            gaps=[],
            evidence_pack='evidence/AF-TEST-01.md',
            validation_commands=[],
            approved_by=None,
            app_testable=True,
            app_surface='test-surface',
            developer_alert='Test item verified, check test-surface.',
        )
    ])
    # Second sync: item transitions to verified → alert created
    store.sync_results([result])
    pending = store.pending_alerts()
    assert len(pending) == 1, f'Expected 1 pending alert, got {len(pending)}'
    assert pending[0].item_id == 'AF-TEST-01'
    assert pending[0].app_surface == 'test-surface'

    # ── Step 8: Shell loads alert as notice ───────────────────────────────
    shell = ShellModel()
    shell.load_pending_app_checks(pending)
    assert len(shell.notices) == 1
    notice_text = shell.notices[0].message
    assert 'AF-TEST-01' in notice_text
    assert 'test-surface' in notice_text

    # ── Step 9: Acknowledgement clears the alert ──────────────────────────
    store.acknowledge('AF-TEST-01')
    assert store.pending_alerts() == []

    # ── Step 10: pending_app_checks.json shows empty pending list ─────────
    pending_payload = json.loads(store.pending_path.read_text(encoding='utf-8'))
    assert pending_payload['pending'] == []
