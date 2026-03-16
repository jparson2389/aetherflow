from datetime import UTC
from pathlib import Path

from aetherflow.core.audit_log import AuditLog


def test_audit_log_records_metadata_and_timestamp(tmp_path: Path) -> None:
    log = AuditLog(storage_path=tmp_path / 'admin_audit.ndjson')

    log.record(
        action='assign_entitlement',
        actor='admin@example.com',
        target='user-123',
        metadata={'ip': '127.0.0.1'},
    )

    entry = log.entries[0]
    assert entry.metadata['ip'] == '127.0.0.1'
    assert entry.timestamp_utc.tzinfo is UTC


def test_audit_log_exports_payload(tmp_path: Path) -> None:
    log = AuditLog(storage_path=tmp_path / 'admin_audit.ndjson')

    log.record(action='create_user', actor='operator', target='user-456')

    payload = log.export_payload()
    assert payload[0]['action'] == 'create_user'
    assert isinstance(payload[0]['timestamp_utc'], str)
    assert payload[0]['metadata'] == {}
