from typing import ClassVar

from aetherflow.ui.panels.capture_panel import CapturePanelModel
from aetherflow.vision.opencv_capture import (
    CaptureDevice,
    CaptureMode,
    OpenCVCapturePlugin,
)


class _ObsOnlyProbe:
    """Minimal probe that exposes only the OBS Virtual Camera for testing."""

    _OBS_DEVICE = CaptureDevice(
        stable_id='capture-device-obs-virtual',
        name='OBS Virtual Camera',
        device_id='device-obs-virtual',
        backend_index=0,
    )
    _OBS_MODES: ClassVar[list[CaptureMode]] = [
        CaptureMode(
            capture_width=1920,
            capture_height=1080,
            capture_fps=30,
            pixel_format_in='RGB32',
            pixel_format_out='BGR',
            zero_copy_supported=False,
            hdr_supported=False,
            notes='Probed candidate mode',
        ),
        CaptureMode(
            capture_width=1920,
            capture_height=1080,
            capture_fps=60,
            pixel_format_in='NV12',
            pixel_format_out='BGR',
            zero_copy_supported=False,
            hdr_supported=False,
            notes='Probed candidate mode',
        ),
    ]

    def enumerate_devices(self) -> list[CaptureDevice]:
        return [self._OBS_DEVICE]

    def supported_modes(self, device: CaptureDevice) -> list[CaptureMode]:  # noqa: ARG002
        return list(self._OBS_MODES)


def test_capture_panel_hides_unsupported_modes() -> None:
    plugin = OpenCVCapturePlugin(probe=_ObsOnlyProbe())
    panel = CapturePanelModel.from_plugin(plugin)
    selector = panel.mode_selector_for('capture-device-obs-virtual')

    assert selector.available_fps == [30, 60]
    assert selector.available_resolutions == [(1920, 1080)]
    assert selector.is_supported(width=1920, height=1080, fps=60) is True
    assert selector.is_supported(width=2560, height=1440, fps=240) is False
    assert (
        selector.unavailable_reason_for(width=2560, height=1440, fps=240)
        == 'Bandwidth and backend limits'
    )
    assert selector.unavailable_reason == 'Bandwidth and backend limits'
