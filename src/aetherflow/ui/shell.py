"""Minimal shell composition models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ShellModel:
    """Top-level shell state."""

    title: str = "Aetherflow"
    active_panels: list[str] = field(default_factory=list)
