from aetherflow.vision.opencv_capture import OpenCVCapturePlugin


def test_opencv_capture_has_120fps_path() -> None:
    plugin = OpenCVCapturePlugin()
    modes = [
        mode
        for device in plugin.enumerate_devices()
        for mode in plugin.supported_modes(device.stable_id)
    ]

    assert any(mode.capture_fps == 120 for mode in modes)


def test_240fps_only_on_capability_device() -> None:
    plugin = OpenCVCapturePlugin()
    for device in plugin.enumerate_devices():
        modes = plugin.supported_modes(device.stable_id)
        if any(mode.capture_fps == 240 for mode in modes):
            assert device.stable_id == 'device-elgato-4kx'
