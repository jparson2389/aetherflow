"""Render mode panel models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RenderMode:
    """Render mode summary."""

    mode_id: str
    latency_priority: str
    cpu_load: str


@dataclass(frozen=True, slots=True)
class RenderModePanelModel:
    """Render mode panel state."""

    modes: list[RenderMode]

    @classmethod
    def default(cls) -> "RenderModePanelModel":
        """Return the default render mode set."""
        return cls(
            modes=[
                RenderMode(
                    mode_id="render.cpu",
                    latency_priority="lowest",
                    cpu_load="highest",
                ),
                RenderMode(
                    mode_id="render.gpu",
                    latency_priority="balanced",
                    cpu_load="lower",
                ),
            ]
        )
