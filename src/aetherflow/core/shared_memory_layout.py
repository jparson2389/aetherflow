"""Shared memory layout contract for worker frame exchange."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class FramePixelFormat(StrEnum):
    """Pixel formats supported by the v1 frame pipeline."""

    BGR24 = "BGR24"
    NV12 = "NV12"
    YUY2 = "YUY2"
    MJPEG = "MJPEG"
    RGB32 = "RGB32"


class OverflowPolicy(StrEnum):
    """Ring-buffer overflow policy."""

    DROP_OLDEST = "DROP_OLDEST"


RING_SLOT_COUNT = 4
DEFAULT_FRAME_WIDTH = 1920
DEFAULT_FRAME_HEIGHT = 1080
DEFAULT_STRIDE_BYTES = DEFAULT_FRAME_WIDTH * 3


@dataclass(frozen=True, slots=True)
class FrameMetadata:
    """Metadata stored alongside each frame ring slot."""

    width: int
    height: int
    pixel_format: FramePixelFormat
    stride_bytes: int
    timestamp_ns: int
    sequence_number: int


@dataclass(frozen=True, slots=True)
class RingBufferCursors:
    """Producer/consumer cursors and overflow count."""

    producer_cursor: int
    consumer_cursor: int
    overflow_count: int


@dataclass(frozen=True, slots=True)
class SharedMemoryLayout:
    """Shared memory ring-buffer contract."""

    ring_slot_count: int = RING_SLOT_COUNT
    overflow_policy: OverflowPolicy = OverflowPolicy.DROP_OLDEST
    default_width: int = DEFAULT_FRAME_WIDTH
    default_height: int = DEFAULT_FRAME_HEIGHT
    default_pixel_format: FramePixelFormat = FramePixelFormat.BGR24
    default_stride_bytes: int = DEFAULT_STRIDE_BYTES

    @property
    def frame_bytes(self) -> int:
        """Return the default frame size in bytes."""
        return self.default_height * self.default_stride_bytes
