import pytest

from aetherflow.input.events import InputEvent, InputEventKind
from aetherflow.input.listener import FakeOSListener
from aetherflow.input.pipeline import DeviceIngestionPipeline, IngestionState


def _make_event(key: str = 'KEY_A') -> InputEvent:
    return InputEvent(
        kind=InputEventKind.KEY_PRESS,
        device_family='keyboard-mouse',
        timestamp_ns=1000,
        key=key,
    )


def test_initial_state_is_idle() -> None:
    listener = FakeOSListener()
    pipeline = DeviceIngestionPipeline(listener=listener)
    assert pipeline.state is IngestionState.IDLE


def test_start_transitions_to_running() -> None:
    listener = FakeOSListener()
    pipeline = DeviceIngestionPipeline(listener=listener)
    pipeline.start()
    assert pipeline.state is IngestionState.RUNNING


def test_stop_transitions_to_stopped() -> None:
    listener = FakeOSListener()
    pipeline = DeviceIngestionPipeline(listener=listener)
    pipeline.start()
    pipeline.stop()
    assert pipeline.state is IngestionState.STOPPED


def test_stop_is_idempotent() -> None:
    listener = FakeOSListener()
    pipeline = DeviceIngestionPipeline(listener=listener)
    pipeline.start()
    pipeline.stop()
    pipeline.stop()
    assert pipeline.state is IngestionState.STOPPED


def test_subscriber_receives_events() -> None:
    received: list[InputEvent] = []
    listener = FakeOSListener()
    pipeline = DeviceIngestionPipeline(listener=listener)
    pipeline.subscribe(received.append)
    pipeline.start()

    listener.push(_make_event())
    assert len(received) == 1


def test_unsubscribed_handler_stops_receiving() -> None:
    received: list[InputEvent] = []
    listener = FakeOSListener()
    pipeline = DeviceIngestionPipeline(listener=listener)
    pipeline.subscribe(received.append)
    pipeline.start()

    listener.push(_make_event('KEY_A'))
    pipeline.unsubscribe(received.append)
    listener.push(_make_event('KEY_B'))

    assert len(received) == 1


def test_pause_gates_event_delivery() -> None:
    received: list[InputEvent] = []
    listener = FakeOSListener()
    pipeline = DeviceIngestionPipeline(listener=listener)
    pipeline.subscribe(received.append)
    pipeline.start()
    pipeline.pause()

    listener.push(_make_event())
    assert len(received) == 0
    assert pipeline.state is IngestionState.PAUSED


def test_resume_resumes_delivery() -> None:
    received: list[InputEvent] = []
    listener = FakeOSListener()
    pipeline = DeviceIngestionPipeline(listener=listener)
    pipeline.subscribe(received.append)
    pipeline.start()
    pipeline.pause()
    pipeline.resume()

    listener.push(_make_event())
    assert len(received) == 1
    assert pipeline.state is IngestionState.RUNNING


def test_start_on_stopped_raises() -> None:
    listener = FakeOSListener()
    pipeline = DeviceIngestionPipeline(listener=listener)
    pipeline.start()
    pipeline.stop()
    with pytest.raises(RuntimeError, match='Cannot restart'):
        pipeline.start()
