"""Test double for OpenCV capture enumeration used by integration tests."""

from aetherflow.vision.opencv_capture import CaptureDevice, CaptureMode


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
