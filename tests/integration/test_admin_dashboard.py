from __future__ import annotations

from datetime import datetime

from aetherflow.core.audit_log import AuditLog
from aetherflow.ui.panels.admin_panel import AdminPanelModel


def test_admin_panel_exposes_operator_actions() -> None:
    log = AuditLog()
    log.record(
        action='assign_entitlement',
        actor='admin@aetherflow',
        target='user:123',
        metadata={'tier': 'pro'},
    )
    log.record(
        action='revoke_session',
        actor='admin@aetherflow',
        target='session:abc',
        metadata={'reason': 'policy'},
    )
    panel = AdminPanelModel.from_audit_log(log)

    assert panel.actions == [
        'create_user',
        'assign_role',
        'assign_entitlement',
        'revoke_session',
    ]
    assert len(panel.audit_entries) == 2
    first = panel.audit_entries[0]
    second = panel.audit_entries[1]
    assert first['action'] == 'assign_entitlement'
    assert first['actor'] == 'admin@aetherflow'
    assert first['target'] == 'user:123'
    assert first['metadata']['tier'] == 'pro'
    assert datetime.fromisoformat(first['timestamp_utc'])
    assert second['action'] == 'revoke_session'
    assert second['metadata']['reason'] == 'policy'
