"""Capture configuration panel models."""

from __future__ import annotations

from dataclasses import dataclass

from aetherflow.vision.opencv_capture import OpenCVCapturePlugin


@dataclass(frozen=True, slots=True)
class CaptureModeSelector:
    """Mode selector view model for a capture device."""

    available_fps: list[int]
    available_resolutions: list[tuple[int, int]]
    supported_modes: list[tuple[int, int, int]]
    unavailable_reason: str

    def is_supported(self, *, width: int, height: int, fps: int) -> bool:
        """Return whether the exact mode combination is selectable."""
        return (width, height, fps) in self.supported_modes

    def unavailable_reason_for(self, *, width: int, height: int, fps: int) -> str:
        """Return reason text for an unavailable mode combination."""
        if self.is_supported(width=width, height=height, fps=fps):
            return ''
        return self.unavailable_reason


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
        supported_modes = sorted(
            {
                (mode.capture_width, mode.capture_height, mode.capture_fps)
                for mode in modes
            }
        )
        return CaptureModeSelector(
            available_fps=sorted({mode.capture_fps for mode in modes}),
            available_resolutions=sorted(
                {(mode.capture_width, mode.capture_height) for mode in modes}
            ),
            supported_modes=supported_modes,
            unavailable_reason='Bandwidth and backend limits',
        )
