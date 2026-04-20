"""Minimal shell composition models."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from loguru import logger

from aetherflow.core.developer_app_checks import PendingAppCheck
from aetherflow.core.entitlements import EntitlementState, RoleName
from aetherflow.core.runtime_state import RuntimeState
from aetherflow.ui.router import RouterModel
from aetherflow.ui.status_hud import StatusHUDModel

if TYPE_CHECKING:
    from aetherflow.ui.panels.plugin_catalog_panel import PluginCatalogPanelModel


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
    plugin_catalog: PluginCatalogPanelModel | None = None

    def _sync_status_hud(
        self,
        *,
        runtime_state: RuntimeState | None = None,
        entitlement_state: EntitlementState | None = None,
        show_expiry_modal: bool | None = None,
    ) -> None:
        """Update the attached HUD model if one is present."""
        if self.status_hud is None:
            return
        self.status_hud = replace(
            self.status_hud,
            runtime_state=(
                runtime_state
                if runtime_state is not None
                else self.status_hud.runtime_state
            ),
            entitlement_state=(
                entitlement_state
                if entitlement_state is not None
                else self.status_hud.entitlement_state
            ),
            show_expiry_modal=(
                self.status_hud.show_expiry_modal
                if show_expiry_modal is None
                else show_expiry_modal
            ),
        )

    def mark_degraded(self, plugin_id: str) -> None:
        """Record a degraded plugin without terminating the shell."""
        if plugin_id not in self.degraded_plugins:
            self.degraded_plugins.append(plugin_id)
        if self.runtime_state is RuntimeState.RUNNING:
            self.runtime_state = RuntimeState.DEGRADED
        self._sync_status_hud(runtime_state=self.runtime_state)
        self.add_notice(
            message=f'Plugin degraded: {plugin_id}',
            severity='warning',
        )
        logger.warning('Shell marked degraded by plugin: {}', plugin_id)

    def mark_recovering(self, plugin_id: str) -> None:
        """Record a recovering plugin while keeping the shell operational."""
        if plugin_id not in self.degraded_plugins:
            self.degraded_plugins.append(plugin_id)
        if self.runtime_state is not RuntimeState.FAILED:
            self.runtime_state = RuntimeState.RECOVERING
        self._sync_status_hud(runtime_state=self.runtime_state)
        self.add_notice(
            message=f'Plugin recovering: {plugin_id}',
            severity='info',
        )
        logger.info('Shell marked recovering by plugin: {}', plugin_id)

    def mark_failed(self, plugin_id: str, *, reason: str) -> None:
        """Record an unrecoverable plugin failure without terminating the shell."""
        if plugin_id not in self.degraded_plugins:
            self.degraded_plugins.append(plugin_id)
        self.runtime_state = RuntimeState.FAILED
        self._sync_status_hud(runtime_state=self.runtime_state)
        self.add_notice(
            message=f'Plugin failed: {plugin_id} ({reason})',
            severity='error',
        )
        logger.error('Shell recorded plugin failure: {} ({})', plugin_id, reason)

    def record_route_failure(self, route_name: str, *, reason: str) -> None:
        """Record a route failure while keeping the shell alive.

        Args:
            route_name: Name of the route that failed.
            reason: Human-readable failure reason.

        """
        self.router.mark_failed(route_name, reason=reason)
        if self.runtime_state is RuntimeState.RUNNING:
            self.runtime_state = RuntimeState.DEGRADED
        self._sync_status_hud(runtime_state=self.runtime_state)
        self.add_notice(
            message=f'Route failed: {route_name}',
            severity='error',
        )
        logger.warning('Shell recorded route failure: {}', route_name)

    def handle_grace_expiry(self, plugin_id: str, *, route_name: str) -> None:
        """Unload only the affected premium route when grace expires.

        Args:
            plugin_id: Premium plugin identifier whose grace expired.
            route_name: Route backed by the premium feature.

        """
        if plugin_id not in self.degraded_plugins:
            self.degraded_plugins.append(plugin_id)
        self.runtime_state = RuntimeState.DEGRADED
        self.router.set_route_lock(route_name, reason='grace-expired')
        route = self.router.routes.get(route_name)
        if route is not None:
            if self.router.active_route == route_name:
                self.router.active_route = None
            if route.panel_id in self.active_panels:
                self.active_panels.remove(route.panel_id)
        self._sync_status_hud(
            runtime_state=self.runtime_state,
            entitlement_state=EntitlementState.LOCKED,
            show_expiry_modal=True,
        )
        self.add_notice(
            message=f'Grace expired: {plugin_id}',
            severity='warning',
        )
        logger.warning('Grace expired for plugin: {}', plugin_id)

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

    def set_plugin_catalog(self, catalog: PluginCatalogPanelModel) -> None:
        """Update the plugin catalog model.

        Args:
            catalog: New plugin catalog panel model.

        """
        self.plugin_catalog = catalog

    def set_active_route(self, route_name: str, *, role: RoleName | None) -> str:
        """Activate a route and track its panel.

        Args:
            route_name: Name of the route to activate.
            role: Active role attempting navigation.

        Returns:
            Panel id for the active route.

        Raises:
            PermissionError: If the route is not accessible to the current role
                or is locked.

        """
        try:
            panel_id = self.router.navigate(route_name, role=role)
        except PermissionError:
            logger.debug('Shell blocked navigation to locked route: {}', route_name)
            raise
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
