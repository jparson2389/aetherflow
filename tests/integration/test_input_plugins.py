from aetherflow.input.kbm import KeyboardMouseInputPlugin
from aetherflow.input.playstation import PlayStationInputPlugin
from aetherflow.input.xinput import XInputPlugin


def test_input_plugins_report_supported_families() -> None:
    xinput = XInputPlugin()
    assert xinput.device_family == 'xinput'
    assert xinput.supports_device('Xbox Wireless Controller')
    assert not xinput.supports_device('DualSense')

    modern = PlayStationInputPlugin(legacy=False)
    assert modern.device_family == 'playstation-modern'
    assert modern.supports_device('DualSense Edge')
    assert not modern.supports_device('DualShock2')

    legacy = PlayStationInputPlugin(legacy=True)
    assert legacy.device_family == 'playstation-legacy'
    assert legacy.supports_device('DualShock2')
    assert not legacy.supports_device('DualSense')

    kbm = KeyboardMouseInputPlugin()
    assert kbm.device_family == 'keyboard-mouse'
    assert kbm.supports_device('USB Keyboard')
    assert kbm.supports_device('Gaming Mouse')
