"""Route state for plugin-backed panels."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class RouterModel:
    """Track named routes."""

    routes: dict[str, str] = field(default_factory=dict)
    failed_routes: set[str] = field(default_factory=set)

    def mark_failed(self, route_name: str) -> None:
        """Mark a route as failed without clearing existing routes."""
        self.failed_routes.add(route_name)
