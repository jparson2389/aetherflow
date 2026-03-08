"""Route state for plugin-backed panels."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class RouterModel:
    """Track named routes."""

    routes: dict[str, str] = field(default_factory=dict)
