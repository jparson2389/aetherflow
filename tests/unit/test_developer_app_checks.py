from __future__ import annotations

import json
from pathlib import Path

from src.aetherflow.core.developer_app_checks import PendingAppCheckStore
from src.aetherflow.core.verification_report import VerificationResult


def _result(
    *,
    item_id: str,
    status: str,
    app_testable: bool,
) -> VerificationResult:
    return VerificationResult(
        item_id=item_id,
        title='Feature',
        status=status,
        gaps=[],
        evidence_pack='docs/evidence/example.md',
        validation_commands=['uv run pytest tests/unit/test_example.py'],
        approved_by='qa.lead' if status == 'verified' else None,
        app_testable=app_testable,
        app_surface='main-window' if app_testable else None,
        developer_alert='New feature added, check for functionality'
        if app_testable
        else None,
    )


def test_first_sync_baselines_verified_items_without_spamming_alerts(
    tmp_path: Path,
) -> None:
    store = PendingAppCheckStore(
        pending_path=tmp_path / 'logs' / 'verification' / 'pending_app_checks.json',
        snapshot_path=tmp_path / 'logs' / 'verification' / 'status_snapshot.json',
    )

    store.sync_results(
        [_result(item_id='AF-03-01', status='verified', app_testable=True)]
    )

    assert store.pending_alerts() == []


def test_sync_creates_pending_alert_when_item_newly_becomes_verified(
    tmp_path: Path,
) -> None:
    store = PendingAppCheckStore(
        pending_path=tmp_path / 'logs' / 'verification' / 'pending_app_checks.json',
        snapshot_path=tmp_path / 'logs' / 'verification' / 'status_snapshot.json',
    )
    store.sync_results([_result(item_id='AF-03-01', status='coded', app_testable=True)])

    store.sync_results(
        [_result(item_id='AF-03-01', status='verified', app_testable=True)]
    )

    pending = store.pending_alerts()
    assert len(pending) == 1
    assert pending[0].item_id == 'AF-03-01'
    assert 'check for functionality' in pending[0].message.lower()


def test_acknowledge_removes_pending_alert(tmp_path: Path) -> None:
    store = PendingAppCheckStore(
        pending_path=tmp_path / 'logs' / 'verification' / 'pending_app_checks.json',
        snapshot_path=tmp_path / 'logs' / 'verification' / 'status_snapshot.json',
    )
    store.sync_results([_result(item_id='AF-03-01', status='coded', app_testable=True)])
    store.sync_results(
        [_result(item_id='AF-03-01', status='verified', app_testable=True)]
    )

    store.acknowledge('AF-03-01')

    assert store.pending_alerts() == []
    payload = json.loads(store.pending_path.read_text(encoding='utf-8'))
    assert payload['pending'] == []
