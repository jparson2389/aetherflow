from aetherflow.ui.panels.capture_panel import CapturePanelModel
from aetherflow.vision.opencv_capture import (
    CaptureDevice,
    CaptureMode,
    OpenCVCapturePlugin,
)


class FakeCaptureProbe:
    def enumerate_devices(self) -> list[CaptureDevice]:
        return [
            CaptureDevice(
                stable_id='capture-swb-obs-virtual-camera',
                name='OBS Virtual Camera',
                device_id='SWB\\OBSVirtualCamera\\OBSVCAM',
                backend_index=1,
            )
        ]

    def supported_modes(self, device: CaptureDevice) -> list[CaptureMode]:
        if device.stable_id != 'capture-swb-obs-virtual-camera':
            return []
        return [
            CaptureMode(
                1280,
                720,
                30,
                'RGB32',
                'BGR',
                False,
                False,
                'Virtual camera',
            ),
            CaptureMode(
                1920,
                1080,
                60,
                'RGB32',
                'BGR',
                False,
                False,
                'Virtual camera',
            ),
        ]


def test_capture_panel_hides_unsupported_modes() -> None:
    plugin = OpenCVCapturePlugin(probe=FakeCaptureProbe())
    panel = CapturePanelModel.from_plugin(plugin)
    selector = panel.mode_selector_for('capture-swb-obs-virtual-camera')

    assert selector.available_fps == [30, 60]
    assert selector.available_resolutions == [(1280, 720), (1920, 1080)]
    assert selector.is_supported(width=1920, height=1080, fps=60) is True
    assert selector.is_supported(width=2560, height=1440, fps=240) is False
    assert (
        selector.unavailable_reason_for(width=2560, height=1440, fps=240)
        == 'Bandwidth and backend limits'
    )
    assert selector.unavailable_reason == 'Bandwidth and backend limits'
