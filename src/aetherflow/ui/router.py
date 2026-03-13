"""Route state for plugin-backed panels."""

from __future__ import annotations

from dataclasses import dataclass, field

from loguru import logger

from aetherflow.core.entitlements import RoleName


@dataclass(slots=True)
class RouteDefinition:
    """Define a named route for a panel."""

    name: str
    title: str
    panel_id: str
    allowed_roles: tuple[RoleName, ...] = ()

    def is_visible(self, role: RoleName | None) -> bool:
        """Return whether the route is visible to a role.

        Args:
            role: Role for the active session.

        Returns:
            True when the role may view the route.

        """
        if not self.allowed_roles:
            return True
        if role is None:
            return False
        return role in self.allowed_roles


@dataclass(slots=True)
class RouterModel:
    """Track named routes and active navigation state."""

    routes: dict[str, RouteDefinition] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)
    active_route: str | None = None
    failed_routes: dict[str, str] = field(default_factory=dict)

    def register_route(self, route: RouteDefinition) -> None:
        """Register a route definition.

        Args:
            route: Route metadata for the panel.

        """
        if route.name not in self.routes:
            self.order.append(route.name)
        self.routes[route.name] = route
        logger.debug('Registered route: {}', route.name)

    def available_routes(self, *, role: RoleName | None = None) -> list[RouteDefinition]:
        """Return routes visible to the provided role.

        Args:
            role: Role for the active session.

        Returns:
            Visible routes in the registration order.

        """
        return [
            self.routes[name]
            for name in self.order
            if self.routes[name].is_visible(role)
        ]

    def navigate(self, route_name: str) -> str:
        """Activate a route and return its panel identifier.

        Args:
            route_name: Name of the route to activate.

        Returns:
            The panel identifier for the active route.

        Raises:
            KeyError: If the route is unknown.

        """
        if route_name not in self.routes:
            raise KeyError(f'Unknown route: {route_name}')
        self.active_route = route_name
        logger.debug('Navigated to route: {}', route_name)
        return self.routes[route_name].panel_id

    def active_panel_id(self) -> str | None:
        """Return the panel id for the active route.

        Returns:
            Panel identifier or None if inactive.

        """
        if self.active_route is None:
            return None
        return self.routes[self.active_route].panel_id

    def mark_failed(self, route_name: str, *, reason: str) -> None:
        """Mark a route as failed without clearing existing routes.

        Args:
            route_name: Name of the failed route.
            reason: Human-readable failure reason.

        """
        self.failed_routes[route_name] = reason
        logger.warning('Route failed: {} ({})', route_name, reason)

    def clear_failure(self, route_name: str) -> None:
        """Clear a failed route marker.

        Args:
            route_name: Name of the route to clear.

        """
        self.failed_routes.pop(route_name, None)
