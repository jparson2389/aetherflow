"""Admin dashboard panel model."""

from __future__ import annotations

from dataclasses import dataclass

from aetherflow.core.audit_log import AuditLog


@dataclass(frozen=True, slots=True)
class AdminPanelModel:
    """Admin panel state."""

    actions: list[str]
    audit_entries: list[dict[str, object]]

    @classmethod
    def from_audit_log(cls, log: AuditLog) -> AdminPanelModel:
        """Build an admin panel model from the audit log.

        Args:
            log: Audit log containing recent admin actions.

        Returns:
            Admin panel view model.

        """
        return cls(
            actions=[
                'create_user',
                'assign_role',
                'assign_entitlement',
                'revoke_session',
            ],
            audit_entries=log.export_payload(),
        )
