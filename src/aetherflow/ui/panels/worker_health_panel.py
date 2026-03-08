"""Worker health panel model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WorkerHealthPanelModel:
    """UI model for worker health."""

    worker_id: str
    health: str
