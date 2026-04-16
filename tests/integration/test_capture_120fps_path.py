from aetherflow.vision.opencv_capture import (
    CaptureDevice,
    CaptureMode,
    OpenCVCapturePlugin,
)


def test_opencv_capture_has_120fps_path() -> None:
    plugin = OpenCVCapturePlugin()
    modes = [
        mode
        for device in plugin.enumerate_devices()
        for mode in plugin.supported_modes(device.stable_id)
    ]

    assert any(mode.capture_fps == 120 for mode in modes)


class _Fake240fpsProbe:
    """Deterministic probe: only synthetic Elgato-style IDs expose 240 FPS modes."""

    def enumerate_devices(self) -> list[CaptureDevice]:
        return [
            CaptureDevice(
                stable_id='capture-vid-0fd9-pid-00af-elgato',
                name='Fake Elgato',
                device_id='VID_0FD9&PID_00AF',
                backend_index=0,
            ),
            CaptureDevice(
                stable_id='capture-vid-aaaa-pid-bbbb-generic',
                name='Fake Generic',
                device_id='VID_AAAA&PID_BBBB',
                backend_index=1,
            ),
        ]

    def supported_modes(self, device: CaptureDevice) -> list[CaptureMode]:
        common = dict(
            pixel_format_out='BGR',
            zero_copy_supported=False,
            hdr_supported=False,
            notes='fake',
        )
        if 'vid-0fd9' in device.stable_id:
            return [
                CaptureMode(
                    capture_width=1920,
                    capture_height=1080,
                    capture_fps=240,
                    pixel_format_in='NV12',
                    **common,
                ),
                CaptureMode(
                    capture_width=1920,
                    capture_height=1080,
                    capture_fps=60,
                    pixel_format_in='NV12',
                    **common,
                ),
            ]
        return [
            CaptureMode(
                capture_width=1920,
                capture_height=1080,
                capture_fps=60,
                pixel_format_in='NV12',
                **common,
            ),
        ]


def test_240fps_only_on_capability_device() -> None:
    plugin = OpenCVCapturePlugin(probe=_Fake240fpsProbe())
    for device in plugin.enumerate_devices():
        modes = plugin.supported_modes(device.stable_id)
        has_240 = any(mode.capture_fps == 240 for mode in modes)
        assert has_240 == ('vid-0fd9' in device.stable_id)
