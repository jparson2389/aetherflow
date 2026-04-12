from aetherflow.vision.opencv_capture import (
    CaptureDevice,
    CaptureMode,
    OpenCVCapturePlugin,
    WindowsOpenCVCaptureProbe,
)


class FakeCaptureProbe:
    def __init__(self) -> None:
        self._devices = [
            CaptureDevice(
                stable_id='capture-usb-vid-0fd9-pid-0066',
                name='Elgato 4K X',
                device_id='USB\\VID_0FD9&PID_0066\\ELGATO4KX',
                backend_index=0,
            ),
            CaptureDevice(
                stable_id='capture-swb-obs-virtual-camera',
                name='OBS Virtual Camera',
                device_id='SWB\\OBSVirtualCamera\\OBSVCAM',
                backend_index=1,
            ),
        ]
        self._modes = {
            self._devices[0].stable_id: [
                CaptureMode(1280, 720, 60, 'NV12', 'BGR', False, False, 'USB 3.0'),
                CaptureMode(1920, 1080, 120, 'NV12', 'BGR', False, False, 'USB 3.0'),
                CaptureMode(
                    2560,
                    1440,
                    240,
                    'MJPEG',
                    'BGR',
                    False,
                    False,
                    'High bandwidth',
                ),
            ],
            self._devices[1].stable_id: [
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
            ],
        }

    def enumerate_devices(self) -> list[CaptureDevice]:
        return list(self._devices)

    def supported_modes(self, device: CaptureDevice) -> list[CaptureMode]:
        return list(self._modes.get(device.stable_id, []))


def test_opencv_capture_enumerates_supported_modes_per_device() -> None:
    plugin = OpenCVCapturePlugin(probe=FakeCaptureProbe())
    devices = plugin.enumerate_devices()

    assert devices
    assert devices[0].stable_id.startswith('capture-')
    assert devices[0].device_id.startswith('USB\\')
    modes = plugin.supported_modes(devices[0].stable_id)
    assert any(mode.capture_fps == 60 for mode in modes)


def test_opencv_capture_supports_60_fps_baseline() -> None:
    plugin = OpenCVCapturePlugin(probe=FakeCaptureProbe())
    for device in plugin.enumerate_devices():
        modes = plugin.supported_modes(device.stable_id)
        assert any(mode.capture_fps == 60 for mode in modes)


def test_opencv_capture_rejects_unsupported_mode_selection() -> None:
    plugin = OpenCVCapturePlugin(probe=FakeCaptureProbe())

    try:
        plugin.start_capture(
            stable_device_id='capture-swb-obs-virtual-camera',
            capture_width=2560,
            capture_height=1440,
            capture_fps=240,
        )
    except ValueError as exc:
        assert 'unsupported capture mode rejected' in str(exc)
    else:
        raise AssertionError('Expected unsupported capture mode to be rejected.')


def test_opencv_capture_start_stop_yields_measurable_metrics() -> None:
    plugin = OpenCVCapturePlugin(probe=FakeCaptureProbe())
    plugin.start_capture(
        stable_device_id='capture-swb-obs-virtual-camera',
        capture_width=1920,
        capture_height=1080,
        capture_fps=60,
    )
    for index in range(60):
        plugin.record_capture_sample(
            'capture-swb-obs-virtual-camera',
            timestamp_s=index / 60.0,
        )

    metrics = plugin.stop_capture('capture-swb-obs-virtual-camera')

    assert metrics.target_fps == 60
    assert metrics.measured_fps >= 60.0
    assert metrics.is_stable is True


def test_opencv_probe_maps_elgato_4k_s_capture_matrix_from_vid_pid() -> None:
    probe = WindowsOpenCVCaptureProbe()
    device = CaptureDevice(
        stable_id='capture-usb-vid-0fd9-pid-00af-mi-00',
        name='Elgato 4K S',
        device_id='USB\\VID_0FD9&PID_00AF&MI_00\\9&27FBDE15&0&0000',
        backend_index=0,
    )

    modes = probe._fallback_modes_for(device)

    assert [
        (mode.capture_width, mode.capture_height, mode.capture_fps) for mode in modes
    ] == [
        (1920, 1080, 30),
        (1920, 1080, 60),
        (1920, 1080, 120),
        (1920, 1080, 240),
        (2560, 1440, 30),
        (2560, 1440, 60),
        (2560, 1440, 120),
        (2560, 1440, 144),
        (3840, 2160, 30),
        (3840, 2160, 60),
    ]
    assert all('USB-C 3.2 Gen1 5Gbps' in mode.notes for mode in modes)
    assert {
        (mode.capture_width, mode.capture_height, mode.capture_fps)
        for mode in modes
        if mode.hdr_supported
    } == {
        (1920, 1080, 30),
        (1920, 1080, 60),
    }
    assert (1920, 1080, 144) not in {
        (mode.capture_width, mode.capture_height, mode.capture_fps) for mode in modes
    }
