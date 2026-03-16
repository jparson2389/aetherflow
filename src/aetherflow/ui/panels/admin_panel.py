"""Admin dashboard panel model."""

from __future__ import annotations

from dataclasses import dataclass

from aetherflow.core.audit_log import AuditLog
from aetherflow.core.entitlements import RoleName


@dataclass(frozen=True, slots=True)
class AdminPanelModel:
    """Admin panel state."""

    actions: list[str]
    audit_entries: list[dict[str, object]]

    @classmethod
    def from_audit_log(
        cls,
        log: AuditLog,
        *,
        role: RoleName,
    ) -> AdminPanelModel:
        """Build an admin panel model from the audit log.

        Args:
            log: Audit log containing recent admin actions.
            role: Active role requesting the admin surface.

        Returns:
            Admin panel view model.

        """
        if role is not RoleName.ADMIN_OPERATOR:
            raise PermissionError('Admin panel access requires Admin/Operator role.')
        return cls(
            actions=[
                'create_user',
                'assign_role',
                'assign_entitlement',
                'revoke_session',
            ],
            audit_entries=log.export_payload(),
        )
