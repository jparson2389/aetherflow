"""Driver status panel model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DriverStatusPanelModel:
    """Driver installation and masking status."""

    installed: bool
    actions: list[str]
    message: str

    @classmethod
    def installed(cls) -> "DriverStatusPanelModel":
        """Return the installed-driver state."""
        return cls(
            installed=True,
            actions=["repair", "disable_masking"],
            message="Driver installed; reversible masking actions available.",
        )
