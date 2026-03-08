"""Driver status panel model."""

from __future__ import annotations

from dataclasses import dataclass

from aetherflow.core.runtime_state import RuntimeState


@dataclass(frozen=True, slots=True)
class DriverStatusPanelModel:
    """Driver installation and masking status."""

    installed: bool
    actions: list[str]
    message: str
    runtime_state: RuntimeState = RuntimeState.RUNNING

    @classmethod
    def for_installed_driver(cls) -> DriverStatusPanelModel:
        """Return the installed-driver state."""
        return cls(
            installed=True,
            actions=["repair", "disable_masking"],
            message="Driver installed; reversible masking actions available.",
            runtime_state=RuntimeState.RUNNING,
        )

    @classmethod
    def for_failed_driver(cls) -> DriverStatusPanelModel:
        """Return the failed-driver state."""
        return cls(
            installed=False,
            actions=["retry", "copy_diagnostics"],
            message="Driver failed; output disabled until recovery.",
            runtime_state=RuntimeState.FAILED,
        )
