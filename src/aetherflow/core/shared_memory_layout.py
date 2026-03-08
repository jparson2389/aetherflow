"""Shared memory layout contract for worker frame exchange."""

from __future__ import annotations

from dataclasses import dataclass


FRAME_RING_SLOTS = 4
DEFAULT_FRAME_WIDTH = 1920
DEFAULT_FRAME_HEIGHT = 1080
DEFAULT_CHANNELS = 3


@dataclass(frozen=True, slots=True)
class SharedMemoryLayout:
    """Shared memory ring-buffer contract."""

    slots: int = FRAME_RING_SLOTS
    width: int = DEFAULT_FRAME_WIDTH
    height: int = DEFAULT_FRAME_HEIGHT
    channels: int = DEFAULT_CHANNELS

    @property
    def frame_bytes(self) -> int:
        """Return the frame size in bytes."""
        return self.width * self.height * self.channels
