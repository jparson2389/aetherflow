from aetherflow.ui.panels.capture_panel import CapturePanelModel
from aetherflow.vision.opencv_capture import OpenCVCapturePlugin


def test_capture_panel_hides_unsupported_modes() -> None:
    plugin = OpenCVCapturePlugin()
    panel = CapturePanelModel.from_plugin(plugin)
    selector = panel.mode_selector_for('device-obs-virtual')

    assert selector.available_fps == [30, 60]
    assert selector.available_resolutions == [(1280, 720), (1920, 1080)]
    assert selector.unavailable_reason == 'Bandwidth and backend limits'
