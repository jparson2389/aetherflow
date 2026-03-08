"""Environment panel model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EnvironmentPanelModel:
    """Environment panel state."""

    env_names: list[str]
