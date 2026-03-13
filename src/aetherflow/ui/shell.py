"""Minimal shell composition models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from loguru import logger

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

    def set_active_route(self, route_name: str) -> str:
        """Activate a route and track its panel.

        Args:
            route_name: Name of the route to activate.

        Returns:
            Panel id for the active route.

        """
        panel_id = self.router.navigate(route_name)
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
