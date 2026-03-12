"""Shared memory layout contract for worker frame exchange."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal


class FramePixelFormat(StrEnum):
    """Pixel formats supported by the v1 frame pipeline."""

    BGR24 = 'BGR24'
    NV12 = 'NV12'
    YUY2 = 'YUY2'
    MJPEG = 'MJPEG'
    RGB32 = 'RGB32'


class OverflowPolicy(StrEnum):
    """Ring-buffer overflow policy."""

    DROP_OLDEST = 'DROP_OLDEST'


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
    """Producer/consumer cursors and overflow counter."""

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


SLOT_ALIGNMENT_BYTES = 64
RING_LAYOUT_VERSION = 1
RING_MAGIC = b'AETHFRM1'


PixelFormat = Literal['BGR24', 'BGRA32', 'RGBA32', 'NV12', 'GRAY8']


_BYTES_PER_PIXEL: dict[PixelFormat, int] = {
    'BGR24': 3,
    'BGRA32': 4,
    'RGBA32': 4,
    'NV12': 2,
    'GRAY8': 1,
}


@dataclass(slots=True, frozen=True)
class FrameRingHeader:
    """Logical header used by host and worker for frame ring coordination."""

    width: int
    height: int
    pixel_format: PixelFormat
    slot_count: int
    slot_stride_bytes: int
    layout_version: int = RING_LAYOUT_VERSION
    magic: bytes = RING_MAGIC

    def validate(self) -> None:
        """Validate structural invariants for the ring header.

        Raises:
            ValueError: If any invariants fail.

        """
        if self.magic != RING_MAGIC:
            raise ValueError('Invalid ring magic.')
        if self.layout_version != RING_LAYOUT_VERSION:
            raise ValueError('Unsupported ring layout version.')
        if self.width <= 0 or self.height <= 0:
            raise ValueError('Frame dimensions must be positive.')
        if self.slot_count < 2:
            raise ValueError(
                'slot_count must be at least 2 for producer/consumer overlap.'
            )
        if self.slot_stride_bytes <= 0:
            raise ValueError('slot_stride_bytes must be positive.')
        if self.slot_stride_bytes % SLOT_ALIGNMENT_BYTES != 0:
            raise ValueError('slot_stride_bytes must be aligned to 64 bytes.')

        minimum_stride = expected_slot_size_bytes(
            width=self.width,
            height=self.height,
            pixel_format=self.pixel_format,
        )
        if self.slot_stride_bytes < minimum_stride:
            raise ValueError('slot_stride_bytes is too small for one full frame.')


@dataclass(slots=True, frozen=True)
class FrameSlotDescriptor:
    """Descriptor for one slot payload in the shared-memory ring."""

    slot_index: int
    offset_bytes: int
    length_bytes: int

    def validate(self, *, slot_count: int, slot_stride_bytes: int) -> None:
        """Validate descriptor alignment and containment within the ring.

        Raises:
            ValueError: If alignment or bounds invariants fail.

        """
        if self.slot_index < 0 or self.slot_index >= slot_count:
            raise ValueError('slot_index out of range.')
        if self.offset_bytes < 0:
            raise ValueError('offset_bytes must be non-negative.')
        if self.length_bytes <= 0:
            raise ValueError('length_bytes must be positive.')
        if self.length_bytes > slot_stride_bytes:
            raise ValueError('length_bytes exceeds slot_stride_bytes.')
        if self.offset_bytes % SLOT_ALIGNMENT_BYTES != 0:
            raise ValueError('offset_bytes must be 64-byte aligned.')


@dataclass(slots=True, frozen=True)
class SharedFrameRingLayout:
    """Layout contract describing header plus slot descriptors."""

    header: FrameRingHeader
    slots: tuple[FrameSlotDescriptor, ...]

    def validate(self) -> None:
        """Validate layout invariants for the header and slot descriptors.

        Raises:
            ValueError: If header or slot descriptors are invalid.

        """
        self.header.validate()
        if len(self.slots) != self.header.slot_count:
            raise ValueError('Slot descriptor count does not match header slot_count.')

        expected_offset = 0
        for descriptor in self.slots:
            descriptor.validate(
                slot_count=self.header.slot_count,
                slot_stride_bytes=self.header.slot_stride_bytes,
            )
            if descriptor.offset_bytes != expected_offset:
                raise ValueError('Slot offsets must be contiguous and deterministic.')
            expected_offset += self.header.slot_stride_bytes


def expected_slot_size_bytes(
    *, width: int, height: int, pixel_format: PixelFormat
) -> int:
    """Return frame payload size rounded up to 64-byte slot alignment.

    Args:
        width: Frame width in pixels.
        height: Frame height in pixels.
        pixel_format: Pixel format identifier.

    Returns:
        Minimal slot size in bytes aligned to 64 bytes.

    Raises:
        ValueError: If the requested dimensions are not positive.

    """
    if width <= 0 or height <= 0:
        raise ValueError('Dimensions must be positive.')

    bytes_per_pixel = _BYTES_PER_PIXEL[pixel_format]
    raw_size = width * height * bytes_per_pixel
    remainder = raw_size % SLOT_ALIGNMENT_BYTES
    if remainder == 0:
        return raw_size
    return raw_size + (SLOT_ALIGNMENT_BYTES - remainder)


def build_layout(
    *, width: int, height: int, pixel_format: PixelFormat, slot_count: int
) -> SharedFrameRingLayout:
    """Build a deterministic contiguous shared-memory frame ring layout.

    Raises:
        ValueError: If any derived invariants fail during layout construction.

    """
    slot_stride_bytes = expected_slot_size_bytes(
        width=width,
        height=height,
        pixel_format=pixel_format,
    )
    header = FrameRingHeader(
        width=width,
        height=height,
        pixel_format=pixel_format,
        slot_count=slot_count,
        slot_stride_bytes=slot_stride_bytes,
    )
    slots = tuple(
        FrameSlotDescriptor(
            slot_index=index,
            offset_bytes=index * slot_stride_bytes,
            length_bytes=slot_stride_bytes,
        )
        for index in range(slot_count)
    )
    layout = SharedFrameRingLayout(header=header, slots=slots)
    layout.validate()
    return layout
