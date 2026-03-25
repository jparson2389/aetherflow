import dataclasses

import pytest

from aetherflow.input.events import InputEvent, InputEventKind, MappedEvent


def test_input_event_kind_has_all_kbm_types() -> None:
    expected = {
        'KEY_PRESS',
        'KEY_RELEASE',
        'MOUSE_MOVE',
        'MOUSE_BUTTON_PRESS',
        'MOUSE_BUTTON_RELEASE',
        'MOUSE_SCROLL',
    }
    assert {k.name for k in InputEventKind} == expected


def test_input_event_is_frozen() -> None:
    event = InputEvent(
        kind=InputEventKind.KEY_PRESS,
        device_family='keyboard-mouse',
        timestamp_ns=1000,
        key='KEY_A',
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        event.key = 'KEY_B'  # type: ignore[misc]


def test_input_event_stores_all_fields() -> None:
    event = InputEvent(
        kind=InputEventKind.MOUSE_MOVE,
        device_family='keyboard-mouse',
        timestamp_ns=5000,
        position=(100, 200),
    )
    assert event.kind is InputEventKind.MOUSE_MOVE
    assert event.device_family == 'keyboard-mouse'
    assert event.timestamp_ns == 5000
    assert event.position == (100, 200)
    assert event.key is None
    assert event.delta is None


def test_mapped_event_carries_latency() -> None:
    source = InputEvent(
        kind=InputEventKind.KEY_PRESS,
        device_family='keyboard-mouse',
        timestamp_ns=1000,
        key='KEY_A',
    )
    mapped = MappedEvent(
        source=source,
        controls=(('KEY_A', True),),
        latency_ns=500,
    )
    assert mapped.latency_ns == 500
    assert mapped.controls == (('KEY_A', True),)
    assert mapped.source is source
