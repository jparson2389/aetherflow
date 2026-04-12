from aetherflow.core.profiles import ProfileStore
from aetherflow.input.events import InputEvent, InputEventKind
from aetherflow.input.kbm import KeyboardMouseInputPlugin
from aetherflow.input.listener import FakeOSListener
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


def test_kbm_pipeline_emits_latency_diagnostics_for_fixture_events() -> None:
    store = ProfileStore()
    store.create('Default')
    listener = FakeOSListener()
    plugin = KeyboardMouseInputPlugin()
    ingestion, mapping = plugin.create_pipeline(
        profile_store=store,
        listener=listener,
    )
    results = []
    mapping.subscribe(results.append)

    ingestion.start()
    listener.push(
        InputEvent(
            kind=InputEventKind.KEY_PRESS,
            device_family='keyboard-mouse',
            timestamp_ns=1000,
            key='KEY_A',
        )
    )
    listener.push(
        InputEvent(
            kind=InputEventKind.MOUSE_MOVE,
            device_family='keyboard-mouse',
            timestamp_ns=2000,
            position=(320, 240),
        )
    )

    snapshot = mapping.diagnostics_snapshot()

    assert len(results) == 2
    assert mapping.telemetry.sample_count == 2
    assert snapshot.event_rate_hz > 0.0
    assert snapshot.output_rate_hz > 0.0
    assert snapshot.latency_ms >= 0.0
    assert snapshot.jitter_ms >= 0.0
