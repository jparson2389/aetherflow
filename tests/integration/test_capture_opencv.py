import pytest

from aetherflow.vision.opencv_capture import (
    CaptureDevice,
    OpenCVCapturePlugin,
    WindowsOpenCVCaptureProbe,
)
from tests.fixtures.fake_opencv_capture_probe import FakeCaptureProbe


def test_opencv_capture_enumerates_supported_modes_per_device() -> None:
    plugin = OpenCVCapturePlugin(probe=FakeCaptureProbe())
    devices = plugin.enumerate_devices()

    assert devices
    assert devices[0].stable_id.startswith('capture-')
    modes = plugin.supported_modes(devices[0].stable_id)
    assert modes
    assert all(mode.capture_width > 0 and mode.capture_fps > 0 for mode in modes)


def test_opencv_capture_supports_60_fps_baseline(
    fake_capture_probe,
) -> None:
    plugin = OpenCVCapturePlugin(probe=fake_capture_probe)
    for device in plugin.enumerate_devices():
        modes = plugin.supported_modes(device.stable_id)
        assert any(mode.capture_fps == 60 for mode in modes)


def test_opencv_capture_rejects_unsupported_mode_selection(
    fake_capture_probe,
) -> None:
    plugin = OpenCVCapturePlugin(probe=fake_capture_probe)

    with pytest.raises(ValueError) as excinfo:
        plugin.start_capture(
            stable_device_id='capture-swb-obs-virtual-camera',
            capture_width=2560,
            capture_height=1440,
            capture_fps=240,
        )

    assert 'unsupported capture mode rejected' in str(excinfo.value)


def test_opencv_capture_start_stop_yields_measurable_metrics(
    fake_capture_probe,
) -> None:
    plugin = OpenCVCapturePlugin(probe=fake_capture_probe)
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

    modes = probe.supported_modes(device)

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


def test_opencv_probe_conservative_fallback_for_unknown_device() -> None:
    probe = WindowsOpenCVCaptureProbe()
    device = CaptureDevice(
        stable_id='capture-usb-vid-1234-pid-5678',
        name='Unknown Capture Device',
        device_id='USB\\VID_1234&PID_5678\\UNKNOWN',
        backend_index=0,
    )

    modes = probe._fallback_modes_for(device)

    fps_values = {mode.capture_fps for mode in modes}
    assert fps_values.isdisjoint({120, 144, 240})
    assert any(
        mode.capture_width == 1920
        and mode.capture_height == 1080
        and mode.capture_fps == 30
        for mode in modes
    )
    assert any(
        mode.capture_width == 1920
        and mode.capture_height == 1080
        and mode.capture_fps == 60
        for mode in modes
    )


def test_opencv_capture_records_dropped_frames_in_session_metrics() -> None:
    plugin = OpenCVCapturePlugin(probe=FakeCaptureProbe())
    stable_id = 'capture-swb-obs-virtual-camera'

    plugin.start_capture(
        stable_device_id=stable_id,
        capture_width=1920,
        capture_height=1080,
        capture_fps=60,
    )

    delivered = 57
    dropped = 3
    for index in range(delivered):
        plugin.record_capture_sample(stable_id, timestamp_s=index / 60.0)
    for index in range(dropped):
        plugin.record_capture_sample(
            stable_id, timestamp_s=(delivered + index) / 60.0, dropped=True
        )

    metrics = plugin.stop_capture(stable_id)

    assert metrics.dropped_frames == dropped
    assert metrics.frames_total == delivered + dropped
