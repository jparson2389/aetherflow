"""Canonical event models for the input pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class InputEventKind(StrEnum):
    """Supported input event types."""

    KEY_PRESS = 'key_press'
    KEY_RELEASE = 'key_release'
    MOUSE_MOVE = 'mouse_move'
    MOUSE_BUTTON_PRESS = 'mouse_button_press'
    MOUSE_BUTTON_RELEASE = 'mouse_button_release'
    MOUSE_SCROLL = 'mouse_scroll'


@dataclass(frozen=True, slots=True)
class InputEvent:
    """Immutable input event produced by an OS listener."""

    kind: InputEventKind
    device_family: str
    timestamp_ns: int
    key: str | None = None
    position: tuple[int, int] | None = None
    delta: tuple[int, int] | None = None


@dataclass(frozen=True, slots=True)
class MappedEvent:
    """Post-pipeline result after profile translation."""

    source: InputEvent
    controls: tuple[tuple[str, bool | float], ...]
    latency_ns: int
