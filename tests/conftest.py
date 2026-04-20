from __future__ import annotations

import os

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest

from aetherflow.vision.opencv_capture import CaptureDevice, CaptureMode


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register custom pytest options."""
    parser.addoption(
        '--count',
        action='store',
        default='1',
        help='Number of bundle installs to simulate.',
    )


@pytest.fixture(scope='session')
def bundle_install_count(pytestconfig: pytest.Config) -> int:
    """Return the bundle install count from CLI."""
    raw = pytestconfig.getoption('--count')
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = 1
    return max(1, value)


class FakeCaptureProbe:
    """Deterministic capture probe for OpenCV-oriented tests."""

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
            CaptureDevice(
                stable_id='capture-usb-vid-0fd9-pid-00af-mi-00',
                name='Elgato 4K S',
                device_id='USB\\VID_0FD9&PID_00AF&MI_00\\9&27FBDE15&0&0000',
                backend_index=2,
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
            self._devices[2].stable_id: [
                CaptureMode(1920, 1080, 60, 'NV12', 'BGR', False, True, 'USB-C 3.2'),
                CaptureMode(1920, 1080, 120, 'NV12', 'BGR', False, False, 'USB-C 3.2'),
                CaptureMode(3840, 2160, 60, 'MJPEG', 'BGR', False, False, 'USB-C 3.2'),
            ],
        }

    def enumerate_devices(self) -> list[CaptureDevice]:
        return list(self._devices)

    def supported_modes(self, device: CaptureDevice) -> list[CaptureMode]:
        return list(self._modes.get(device.stable_id, []))


@pytest.fixture
def fake_capture_probe() -> FakeCaptureProbe:
    """Return a deterministic capture probe for integration and UI tests."""
    return FakeCaptureProbe()
