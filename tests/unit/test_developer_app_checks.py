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


def test_newly_verified_app_testable_item_creates_pending_alert(tmp_path: Path) -> None:
    """When an item moves to verified with app_testable=True, it appears in pending."""
    store = PendingAppCheckStore(
        pending_path=tmp_path / 'logs' / 'verification' / 'pending_app_checks.json',
        snapshot_path=tmp_path / 'logs' / 'verification' / 'status_snapshot.json',
    )
    store.sync_results([_result(item_id='AF-01-02', status='coded', app_testable=True)])
    store.sync_results([_result(item_id='AF-01-02', status='verified', app_testable=True)])
    pending = store.pending_alerts()
    assert len(pending) == 1
    assert pending[0].item_id == 'AF-01-02'
    assert pending[0].app_surface == 'main-window'
    assert len(pending[0].message) > 0


def test_non_app_testable_item_does_not_create_alert(tmp_path: Path) -> None:
    """app_testable=False item never creates an alert even when verified."""
    store = PendingAppCheckStore(
        pending_path=tmp_path / 'logs' / 'verification' / 'pending_app_checks.json',
        snapshot_path=tmp_path / 'logs' / 'verification' / 'status_snapshot.json',
    )
    store.sync_results([_result(item_id='AF-03-01', status='coded', app_testable=False)])
    store.sync_results([_result(item_id='AF-03-01', status='verified', app_testable=False)])
    assert store.pending_alerts() == []


def test_startup_loads_pending_alerts_into_shell_notices(tmp_path: Path) -> None:
    """shell.load_pending_app_checks() converts entries to notices."""
    from src.aetherflow.ui.shell import ShellModel

    store = PendingAppCheckStore(
        pending_path=tmp_path / 'logs' / 'verification' / 'pending_app_checks.json',
        snapshot_path=tmp_path / 'logs' / 'verification' / 'status_snapshot.json',
    )
    store.sync_results([_result(item_id='AF-01-02', status='coded', app_testable=True)])
    store.sync_results([_result(item_id='AF-01-02', status='verified', app_testable=True)])

    shell = ShellModel()
    shell.load_pending_app_checks(store.pending_alerts())
    assert len(shell.notices) == 1
    assert 'AF-01-02' in shell.notices[0].message


def test_alert_message_includes_item_id_and_surface(tmp_path: Path) -> None:
    """Notice text contains item ID and app_surface."""
    from src.aetherflow.ui.shell import ShellModel

    store = PendingAppCheckStore(
        pending_path=tmp_path / 'logs' / 'verification' / 'pending_app_checks.json',
        snapshot_path=tmp_path / 'logs' / 'verification' / 'status_snapshot.json',
    )
    store.sync_results([_result(item_id='AF-01-02', status='coded', app_testable=True)])
    store.sync_results([_result(item_id='AF-01-02', status='verified', app_testable=True)])

    shell = ShellModel()
    shell.load_pending_app_checks(store.pending_alerts())
    notice_text = shell.notices[0].message
    assert 'AF-01-02' in notice_text
    assert 'main-window' in notice_text


def test_acknowledgement_removes_from_pending(tmp_path: Path) -> None:
    """Once acknowledged, item disappears from pending_app_checks.json."""
    store = PendingAppCheckStore(
        pending_path=tmp_path / 'logs' / 'verification' / 'pending_app_checks.json',
        snapshot_path=tmp_path / 'logs' / 'verification' / 'status_snapshot.json',
    )
    store.sync_results([_result(item_id='AF-01-02', status='coded', app_testable=True)])
    store.sync_results([_result(item_id='AF-01-02', status='verified', app_testable=True)])
    store.acknowledge('AF-01-02')

    assert store.pending_alerts() == []
    payload = json.loads(store.pending_path.read_text(encoding='utf-8'))
    assert payload['pending'] == []


def test_duplicate_startup_does_not_duplicate_alerts(tmp_path: Path) -> None:
    """Loading the same pending checks twice does not add duplicate store entries."""
    from src.aetherflow.ui.shell import ShellModel

    store = PendingAppCheckStore(
        pending_path=tmp_path / 'logs' / 'verification' / 'pending_app_checks.json',
        snapshot_path=tmp_path / 'logs' / 'verification' / 'status_snapshot.json',
    )
    store.sync_results([_result(item_id='AF-01-02', status='coded', app_testable=True)])
    store.sync_results([_result(item_id='AF-01-02', status='verified', app_testable=True)])

    shell = ShellModel()
    alerts = store.pending_alerts()
    shell.load_pending_app_checks(alerts)
    shell.load_pending_app_checks(alerts)  # called twice
    # After re-syncing with same verified status, still only 1 pending alert in the store
    store.sync_results([_result(item_id='AF-01-02', status='verified', app_testable=True)])
    assert len(store.pending_alerts()) == 1


def test_regraded_legacy_items_do_not_create_alerts(tmp_path: Path) -> None:
    """Items whose verification predates the new system are not backfilled."""
    store = PendingAppCheckStore(
        pending_path=tmp_path / 'logs' / 'verification' / 'pending_app_checks.json',
        snapshot_path=tmp_path / 'logs' / 'verification' / 'status_snapshot.json',
    )
    # Initial call with item already verified (legacy item) — should NOT create alert
    store.sync_results([_result(item_id='AF-02-02', status='verified', app_testable=True)])
    assert store.pending_alerts() == []
