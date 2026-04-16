"""Shared capture device, mode, and session resolution for vision backends."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from aetherflow.vision.opencv_capture import (
        CaptureDevice,
        CaptureMode,
        CaptureSession,
    )


class CaptureResolutionSource(Protocol):
    """Backend that lists devices and modes by stable device id."""

    def enumerate_devices(self) -> list[CaptureDevice]:
        """Return available capture devices."""
        ...

    def supported_modes(self, stable_device_id: str) -> list[CaptureMode]:
        """Return supported modes for the given stable device id."""
        ...


class CaptureResolver:
    """Resolve devices, modes, and active sessions with stable error semantics."""

    @staticmethod
    def resolve_device(
        source: CaptureResolutionSource,
        stable_device_id: str,
    ) -> CaptureDevice:
        """Resolve a capture device by stable identifier.

        Args:
            source: Backend that enumerates ``CaptureDevice`` instances.
            stable_device_id: Stable device key to match against ``device.stable_id``.

        Returns:
            The ``CaptureDevice`` whose ``stable_id`` equals ``stable_device_id``.

        Raises:
            KeyError: If no enumerated device matches ``stable_device_id``.

        """
        for device in source.enumerate_devices():
            if device.stable_id == stable_device_id:
                return device
        raise KeyError(f'Unknown capture device: {stable_device_id}')

    @staticmethod
    def resolve_mode(
        source: CaptureResolutionSource,
        *,
        stable_device_id: str,
        capture_width: int,
        capture_height: int,
        capture_fps: int,
    ) -> CaptureMode:
        """Pick the first matching capture mode for a device.

        Iterates ``source.supported_modes(stable_device_id)`` and returns the first
        ``CaptureMode`` whose ``capture_width``, ``capture_height``, and
        ``capture_fps`` exactly match the requested triple (equality match, not
        tolerance).

        Args:
            source: Backend that lists modes per stable device id.
            stable_device_id: Device key passed to ``supported_modes``.
            capture_width: Requested frame width in pixels.
            capture_height: Requested frame height in pixels.
            capture_fps: Requested capture rate in frames per second.

        Returns:
            The first ``CaptureMode`` that matches all three dimensions.

        Raises:
            ValueError: If no listed mode matches the requested width, height,
                and FPS.

        """
        for mode in source.supported_modes(stable_device_id):
            if (
                mode.capture_width == capture_width
                and mode.capture_height == capture_height
                and mode.capture_fps == capture_fps
            ):
                return mode
        raise ValueError('unsupported capture mode rejected')

    @staticmethod
    def active_session(
        sessions: dict[str, CaptureSession],
        stable_device_id: str,
    ) -> CaptureSession:
        """Return the active capture session for a device.

        Args:
            sessions: Map from ``stable_device_id`` to ``CaptureSession``.
            stable_device_id: Stable device key to look up.

        Returns:
            The ``CaptureSession`` for ``stable_device_id`` when it exists and
            ``session.running`` is true.

        Raises:
            RuntimeError: If there is no session for ``stable_device_id``, or the
                session exists but ``running`` is false.

        """
        session = sessions.get(stable_device_id)
        if session is None or not session.running:
            raise RuntimeError(f'Capture not running for {stable_device_id}')
        return session
