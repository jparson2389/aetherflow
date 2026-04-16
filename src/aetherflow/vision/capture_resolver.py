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
        """Return a known device or raise ``KeyError`` for an unknown identifier."""
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
        """Return a supported mode or raise ``ValueError`` when unsupported."""
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
        """Return the running session or raise ``RuntimeError``."""
        session = sessions.get(stable_device_id)
        if session is None or not session.running:
            raise RuntimeError(f'Capture not running for {stable_device_id}')
        return session
