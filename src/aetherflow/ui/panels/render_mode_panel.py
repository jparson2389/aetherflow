"""Render mode panel models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RenderMode:
    """Render mode summary."""

    mode_id: str
    latency_priority: str
    cpu_load: str
    requires_restart: bool


@dataclass(frozen=True, slots=True)
class RenderModePanelModel:
    """Render mode panel state with active mode selection."""

    modes: list[RenderMode]
    active_mode_id: str = 'render.cpu'

    @classmethod
    def default(cls) -> RenderModePanelModel:
        """Return the default render mode set with CPU as active."""
        return cls(
            modes=[
                RenderMode(
                    mode_id='render.cpu',
                    latency_priority='lowest',
                    cpu_load='highest',
                    requires_restart=False,
                ),
                RenderMode(
                    mode_id='render.gpu',
                    latency_priority='balanced',
                    cpu_load='lower',
                    requires_restart=True,
                ),
            ],
            active_mode_id='render.cpu',
        )

    def select(self, mode_id: str) -> RenderModePanelModel:
        """Return a new panel model with the given mode as active.

        Args:
            mode_id: The mode ID to activate.

        Returns:
            A new panel model with the updated active mode.

        Raises:
            ValueError: If the mode_id is not in the available modes.

        """
        valid_ids = {m.mode_id for m in self.modes}
        if mode_id not in valid_ids:
            raise ValueError(
                f'Unknown render mode {mode_id!r}. '
                f'Valid modes: {", ".join(sorted(valid_ids))}'
            )
        return RenderModePanelModel(
            modes=self.modes,
            active_mode_id=mode_id,
        )
