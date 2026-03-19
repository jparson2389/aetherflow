
"""Minimal shell composition models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from loguru import logger

from aetherflow.core.developer_app_checks import PendingAppCheck
from aetherflow.core.entitlements import RoleName
from aetherflow.core.runtime_state import RuntimeState
from aetherflow.ui.router import RouterModel
from aetherflow.ui.status_hud import StatusHUDModel


@dataclass(slots=True)
class ShellNotice:
    """Shell notification entry."""

    message: str
    severity: str
    timestamp_utc: datetime


@dataclass(slots=True)
class ShellModel:
    """Top-level shell state."""

    title: str = 'Aetherflow'
    active_panels: list[str] = field(default_factory=list)
    runtime_state: RuntimeState = RuntimeState.RUNNING
    degraded_plugins: list[str] = field(default_factory=list)
    router: RouterModel = field(default_factory=RouterModel)
    notices: list[ShellNotice] = field(default_factory=list)
    status_hud: StatusHUDModel | None = None

    def mark_degraded(self, plugin_id: str) -> None:
        """Record a degraded plugin without terminating the shell."""
        if plugin_id not in self.degraded_plugins:
            self.degraded_plugins.append(plugin_id)
        if self.runtime_state is RuntimeState.RUNNING:
            self.runtime_state = RuntimeState.DEGRADED
        self.add_notice(
            message=f'Plugin degraded: {plugin_id}',
            severity='warning',
        )
        logger.warning('Shell marked degraded by plugin: {}', plugin_id)

    def record_route_failure(self, route_name: str, *, reason: str) -> None:
        """Record a route failure while keeping the shell alive.

        Args:
            route_name: Name of the route that failed.
            reason: Human-readable failure reason.

        """
        self.router.mark_failed(route_name, reason=reason)
        if self.runtime_state is RuntimeState.RUNNING:
            self.runtime_state = RuntimeState.DEGRADED
        self.add_notice(
            message=f'Route failed: {route_name}',
            severity='error',
        )
        logger.warning('Shell recorded route failure: {}', route_name)

    def add_notice(self, *, message: str, severity: str) -> None:
        """Add a notification to the shell.

        Args:
            message: Notice message.
            severity: Severity tag for the notice.

        """
        self.notices.append(
            ShellNotice(
                message=message,
                severity=severity,
                timestamp_utc=datetime.now(UTC),
            )
        )

    def load_pending_app_checks(self, alerts: list[PendingAppCheck]) -> None:
        """Load pending developer app-check notices into the shell.

        Args:
            alerts: Pending developer alerts from verification results.

        """
        for alert in alerts:
            self.add_notice(
                message=f'{alert.message} [{alert.item_id}: {alert.app_surface}]',
                severity='info',
            )
        if alerts:
            logger.info('Loaded {} pending developer app checks.', len(alerts))

    def set_status_hud(self, hud: StatusHUDModel) -> None:
        """Update the status HUD model.

        Args:
            hud: New status HUD data.

        """
        self.status_hud = hud

    def set_active_route(self, route_name: str, *, role: RoleName | None) -> str:
        """Activate a route and track its panel.

        Args:
            route_name: Name of the route to activate.
            role: Active role attempting navigation.

        Returns:
            Panel id for the active route.

        """
        panel_id = self.router.navigate(route_name, role=role)
        if panel_id not in self.active_panels:
            self.active_panels.append(panel_id)
        logger.debug('Shell activated panel: {}', panel_id)
        return panel_id

    def active_panel_id(self) -> str | None:
        """Return the active panel id if available.

        Returns:
            Active panel id or None.

        """
        return self.router.active_panel_id()
