from aetherflow.vision.opencv_capture import OpenCVCapturePlugin


def test_opencv_capture_enumerates_supported_modes_per_device() -> None:
    plugin = OpenCVCapturePlugin()
    devices = plugin.enumerate_devices()

    assert devices
    assert devices[0].stable_id.startswith('device-')
    modes = plugin.supported_modes(devices[0].stable_id)
    assert any(mode.capture_fps == 60 for mode in modes)


def test_opencv_capture_supports_60_fps_baseline() -> None:
    plugin = OpenCVCapturePlugin()
    for device in plugin.enumerate_devices():
        modes = plugin.supported_modes(device.stable_id)
        assert any(mode.capture_fps == 60 for mode in modes)
