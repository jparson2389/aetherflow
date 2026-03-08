"""Capture diagnostics panel model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CaptureDiagnosticsPanelModel:
    """Diagnostics and fallback actions for unstable capture."""

    recommendation: str
    diagnostics_blob: str

    @property
    def actions(self) -> list[str]:
        """Return available UI actions."""
        return ["apply_recommendation", "copy_diagnostics"]
