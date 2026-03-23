from aetherflow.core.profiles import ProfileStore
from aetherflow.input.events import InputEvent, InputEventKind, MappedEvent
from aetherflow.input.listener import FakeOSListener
from aetherflow.input.mapping import InputLatencyTelemetry, MappingPipeline
from aetherflow.input.pipeline import DeviceIngestionPipeline


def _make_key_event(key: str = 'KEY_A', ts: int = 1000) -> InputEvent:
    return InputEvent(
        kind=InputEventKind.KEY_PRESS,
        device_family='keyboard-mouse',
        timestamp_ns=ts,
        key=key,
    )


def _controls_dict(event: MappedEvent) -> dict:
    return dict(event.controls)


def test_mapping_pipeline_translates_key_press() -> None:
    store = ProfileStore()
    store.create('Default')
    listener = FakeOSListener()
    ingestion = DeviceIngestionPipeline(listener=listener)

    mapped_events: list[MappedEvent] = []
    mapping = MappingPipeline(ingestion=ingestion, profile_store=store)
    mapping.subscribe(mapped_events.append)

    ingestion.start()
    listener.push(_make_key_event('KEY_A'))

    assert len(mapped_events) == 1
    assert _controls_dict(mapped_events[0]).get('KEY_A') is True


def test_mapping_pipeline_applies_button_map() -> None:
    store = ProfileStore()
    profile = store.create('Default')
    profile.button_map['KEY_A'] = 'JUMP'

    listener = FakeOSListener()
    ingestion = DeviceIngestionPipeline(listener=listener)

    mapped_events: list[MappedEvent] = []
    mapping = MappingPipeline(ingestion=ingestion, profile_store=store)
    mapping.subscribe(mapped_events.append)

    ingestion.start()
    listener.push(_make_key_event('KEY_A'))

    assert 'JUMP' in _controls_dict(mapped_events[0])


def test_mapping_pipeline_records_latency() -> None:
    store = ProfileStore()
    store.create('Default')
    listener = FakeOSListener()
    ingestion = DeviceIngestionPipeline(listener=listener)

    mapping = MappingPipeline(ingestion=ingestion, profile_store=store)
    mapping.subscribe(lambda _: None)

    ingestion.start()
    listener.push(_make_key_event())

    assert mapping.telemetry.sample_count == 1


def test_mapping_pipeline_skips_without_active_profile() -> None:
    store = ProfileStore()  # no profile created
    listener = FakeOSListener()
    ingestion = DeviceIngestionPipeline(listener=listener)

    mapped_events: list[MappedEvent] = []
    mapping = MappingPipeline(ingestion=ingestion, profile_store=store)
    mapping.subscribe(mapped_events.append)

    ingestion.start()
    listener.push(_make_key_event())

    assert len(mapped_events) == 0


def test_mapping_pipeline_handles_mouse_move() -> None:
    store = ProfileStore()
    store.create('Default')
    listener = FakeOSListener()
    ingestion = DeviceIngestionPipeline(listener=listener)

    mapped_events: list[MappedEvent] = []
    mapping = MappingPipeline(ingestion=ingestion, profile_store=store)
    mapping.subscribe(mapped_events.append)

    ingestion.start()
    event = InputEvent(
        kind=InputEventKind.MOUSE_MOVE,
        device_family='keyboard-mouse',
        timestamp_ns=1000,
        position=(100, 200),
    )
    listener.push(event)

    assert len(mapped_events) == 1
    controls = _controls_dict(mapped_events[0])
    assert 'MOUSE_X' in controls
    assert 'MOUSE_Y' in controls
