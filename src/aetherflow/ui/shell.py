"""Minimal shell composition models."""

from __future__ import annotations

from dataclasses import dataclass, field

from aetherflow.core.runtime_state import RuntimeState


@dataclass(slots=True)
class ShellModel:
    """Top-level shell state."""

    title: str = 'Aetherflow'
    active_panels: list[str] = field(default_factory=list)
    runtime_state: RuntimeState = RuntimeState.RUNNING
    degraded_plugins: list[str] = field(default_factory=list)

    def mark_degraded(self, plugin_id: str) -> None:
        """Record a degraded plugin without terminating the shell."""
        if plugin_id not in self.degraded_plugins:
            self.degraded_plugins.append(plugin_id)
        if self.runtime_state is RuntimeState.RUNNING:
            self.runtime_state = RuntimeState.DEGRADED
