from aetherflow.core.audit_log import AuditLog
from aetherflow.ui.panels.admin_panel import AdminPanelModel


def test_admin_panel_exposes_operator_actions() -> None:
    log = AuditLog()
    panel = AdminPanelModel.from_audit_log(log)

    assert "assign_entitlement" in panel.actions
    assert panel.audit_entries == []
