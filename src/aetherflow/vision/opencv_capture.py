"""Deterministic OpenCV capture model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CaptureDevice:
    """Capture device descriptor."""

    stable_id: str
    name: str


@dataclass(frozen=True, slots=True)
class CaptureMode:
    """Runtime capture mode descriptor."""

    capture_width: int
    capture_height: int
    capture_fps: int
    pixel_format_in: str
    pixel_format_out: str
    zero_copy_supported: bool
    hdr_supported: bool
    notes: str


class OpenCVCapturePlugin:
    """Default OpenCV-based capture provider."""

    _DEVICES = (
        CaptureDevice(stable_id="device-elgato-4kx", name="Elgato 4K X"),
        CaptureDevice(stable_id="device-obs-virtual", name="OBS Virtual Camera"),
    )
    _MODES = {
        "device-elgato-4kx": [
            CaptureMode(1280, 720, 60, "NV12", "BGR", False, False, "USB 3.0"),
            CaptureMode(1920, 1080, 120, "NV12", "BGR", False, False, "USB 3.0"),
            CaptureMode(
                2560, 1440, 240, "MJPEG", "BGR", False, False, "High bandwidth"
            ),
        ],
        "device-obs-virtual": [
            CaptureMode(1280, 720, 30, "RGB32", "BGR", False, False, "Virtual camera"),
            CaptureMode(1920, 1080, 60, "RGB32", "BGR", False, False, "Virtual camera"),
        ],
    }

    def enumerate_devices(self) -> list[CaptureDevice]:
        """Return available capture devices."""
        return list(self._DEVICES)

    def supported_modes(self, stable_device_id: str) -> list[CaptureMode]:
        """Return supported modes for a device."""
        return list(self._MODES.get(stable_device_id, []))
