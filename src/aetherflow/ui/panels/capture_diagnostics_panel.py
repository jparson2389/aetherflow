"""Capture diagnostics panel model."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from aetherflow.core.diagnostics import PipelineDiagnostics
from aetherflow.ui.panels.render_mode_panel import RenderModePanelModel


@dataclass(frozen=True, slots=True)
class CaptureDiagnosticsPanelModel:
    """Diagnostics and fallback actions for unstable capture."""

    recommendation: str
    diagnostics_blob: str
    metrics: dict[str, float] = field(default_factory=dict)

    @property
    def actions(self) -> list[str]:
        """Return available UI actions."""
        return ['apply_recommendation', 'copy_diagnostics']

    @classmethod
    def from_snapshot(
        cls,
        *,
        recommendation: str,
        snapshot: PipelineDiagnostics,
    ) -> CaptureDiagnosticsPanelModel:
        """Build diagnostics panel data from a snapshot.

        Args:
            recommendation: Recommended capture mode.
            snapshot: Diagnostics snapshot to serialize.

        Returns:
            Capture diagnostics panel model.

        """
        metrics = snapshot.as_dict()
        return cls(
            recommendation=recommendation,
            diagnostics_blob=json.dumps(metrics, indent=2),
            metrics=metrics,
        )

    def apply_recommendation(
        self, render_panel: RenderModePanelModel
    ) -> RenderModePanelModel:
        """Apply the recommended render mode to the given render panel.

        Args:
            render_panel: The current render mode panel model.

        Returns:
            A new render panel model with the recommended mode applied.

        Raises:
            ValueError: If the recommendation is not a valid render mode.

        """
        return render_panel.select(self.recommendation)
