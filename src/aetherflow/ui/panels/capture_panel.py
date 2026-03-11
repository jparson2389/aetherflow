"""Capture configuration panel models."""

from __future__ import annotations

from dataclasses import dataclass

from aetherflow.vision.opencv_capture import OpenCVCapturePlugin


@dataclass(frozen=True, slots=True)
class CaptureModeSelector:
    """Mode selector view model for a capture device."""

    available_fps: list[int]
    available_resolutions: list[tuple[int, int]]
    unavailable_reason: str


@dataclass(slots=True)
class CapturePanelModel:
    """Capture panel view model."""

    plugin: OpenCVCapturePlugin

    @classmethod
    def from_plugin(cls, plugin: OpenCVCapturePlugin) -> CapturePanelModel:
        """Build a panel model from a capture plugin."""
        return cls(plugin=plugin)

    def mode_selector_for(self, stable_device_id: str) -> CaptureModeSelector:
        """Return the mode selector for a device."""
        modes = self.plugin.supported_modes(stable_device_id)
        return CaptureModeSelector(
            available_fps=sorted({mode.capture_fps for mode in modes}),
            available_resolutions=sorted(
                {(mode.capture_width, mode.capture_height) for mode in modes}
            ),
            unavailable_reason='Bandwidth and backend limits',
        )
