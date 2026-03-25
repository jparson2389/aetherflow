from aetherflow.input.events import InputEvent, InputEventKind
from aetherflow.input.listener import FakeOSListener, NullOSListener


def test_fake_listener_delivers_events() -> None:
    received: list[InputEvent] = []
    listener = FakeOSListener()
    listener.start(on_event=received.append)

    event = InputEvent(
        kind=InputEventKind.KEY_PRESS,
        device_family='keyboard-mouse',
        timestamp_ns=1000,
        key='KEY_A',
    )
    listener.push(event)

    assert len(received) == 1
    assert received[0] is event


def test_fake_listener_ignores_push_before_start() -> None:
    listener = FakeOSListener()
    event = InputEvent(
        kind=InputEventKind.KEY_PRESS,
        device_family='keyboard-mouse',
        timestamp_ns=1000,
        key='KEY_A',
    )
    listener.push(event)  # no crash, no delivery


def test_fake_listener_stop_prevents_delivery() -> None:
    received: list[InputEvent] = []
    listener = FakeOSListener()
    listener.start(on_event=received.append)
    listener.stop()

    event = InputEvent(
        kind=InputEventKind.KEY_PRESS,
        device_family='keyboard-mouse',
        timestamp_ns=1000,
        key='KEY_A',
    )
    listener.push(event)
    assert len(received) == 0


def test_null_listener_lifecycle() -> None:
    received: list[InputEvent] = []
    listener = NullOSListener()
    listener.start(on_event=received.append)
    listener.stop()
    assert len(received) == 0
