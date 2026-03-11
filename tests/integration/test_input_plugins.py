from aetherflow.input.kbm import KeyboardMouseInputPlugin
from aetherflow.input.playstation import PlayStationInputPlugin
from aetherflow.input.xinput import XInputPlugin


def test_input_plugins_report_supported_families() -> None:
    assert XInputPlugin().device_family == 'xinput'
    assert PlayStationInputPlugin(legacy=False).device_family == 'playstation-modern'
    assert KeyboardMouseInputPlugin().device_family == 'keyboard-mouse'
