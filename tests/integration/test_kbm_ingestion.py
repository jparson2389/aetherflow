from aetherflow.core.profiles import ProfileStore
from aetherflow.input.events import InputEvent, InputEventKind, MappedEvent
from aetherflow.input.kbm import KeyboardMouseInputPlugin
from aetherflow.input.listener import FakeOSListener


def test_end_to_end_kbm_pipeline() -> None:
    """Full pipeline: FakeOSListener -> Ingestion -> Mapping -> MappedEvent."""
    store = ProfileStore()
    profile = store.create('Default')
    profile.button_map['KEY_A'] = 'JUMP'
    profile.button_map['KEY_D'] = 'STRAFE_RIGHT'

    listener = FakeOSListener()
    plugin = KeyboardMouseInputPlugin()
    ingestion, mapping = plugin.create_pipeline(
        profile_store=store,
        listener=listener,
    )

    results: list[MappedEvent] = []
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
            kind=InputEventKind.KEY_RELEASE,
            device_family='keyboard-mouse',
            timestamp_ns=2000,
            key='KEY_A',
        )
    )
    listener.push(
        InputEvent(
            kind=InputEventKind.MOUSE_MOVE,
            device_family='keyboard-mouse',
            timestamp_ns=3000,
            position=(400, 300),
        )
    )
    listener.push(
        InputEvent(
            kind=InputEventKind.MOUSE_SCROLL,
            device_family='keyboard-mouse',
            timestamp_ns=4000,
            delta=(0, -3),
        )
    )

    assert len(results) == 4

    def _c(idx: int) -> dict:
        return dict(results[idx].controls)

    # Key press mapped through button_map
    assert _c(0).get('JUMP') is True

    # Key release mapped through button_map
    assert _c(1).get('JUMP') is False

    # Mouse move produces axis values
    assert _c(2).get('MOUSE_X') == 400.0
    assert _c(2).get('MOUSE_Y') == 300.0

    # Scroll produces deltas
    assert _c(3).get('SCROLL_DX') == 0.0
    assert _c(3).get('SCROLL_DY') == -3.0

    # Latency telemetry recorded for all events
    assert mapping.telemetry.sample_count == 4

    ingestion.stop()


def test_profile_switch_affects_next_event() -> None:
    """Switching profiles mid-stream changes mapping for the next event."""
    store = ProfileStore()
    p1 = store.create('Default')
    p1.button_map['KEY_W'] = 'FORWARD'
    p2 = store.create('Alt')
    p2.button_map['KEY_W'] = 'UP'

    listener = FakeOSListener()
    plugin = KeyboardMouseInputPlugin()
    ingestion, mapping = plugin.create_pipeline(
        profile_store=store,
        listener=listener,
    )

    results: list[MappedEvent] = []
    mapping.subscribe(results.append)
    ingestion.start()

    event = InputEvent(
        kind=InputEventKind.KEY_PRESS,
        device_family='keyboard-mouse',
        timestamp_ns=1000,
        key='KEY_W',
    )

    # First event uses p1 (active by default since created first)
    listener.push(event)
    assert 'FORWARD' in dict(results[0].controls)

    # Switch to p2
    store.switch_active(p2.profile_id)
    listener.push(event)
    assert 'UP' in dict(results[1].controls)

    ingestion.stop()


def test_kbm_catalog_registration() -> None:
    """KBM plugin appears in the default catalog."""
    from aetherflow.core.entitlements import RoleName
    from aetherflow.ui.bootstrap import _build_default_catalog

    catalog = _build_default_catalog(role=RoleName.POWER_GAMER)
    ids = [e.plugin_id for e in catalog.entries]
    assert 'input.kbm' in ids
    kbm = next(e for e in catalog.entries if e.plugin_id == 'input.kbm')
    assert kbm.selectable is True
    assert kbm.lock_state.value == 'AVAILABLE'
