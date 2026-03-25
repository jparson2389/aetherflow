import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

from aetherflow.core.profiles import ProfileStore
from aetherflow.input.events import InputEvent, InputEventKind
from aetherflow.input.kbm import KeyboardMouseInputPlugin
from aetherflow.input.listener import FakeOSListener


def test_supports_device_matches_known_signatures() -> None:
    plugin = KeyboardMouseInputPlugin()
    assert plugin.device_family == 'keyboard-mouse'
    assert plugin.supports_device('USB Keyboard')
    assert plugin.supports_device('Gaming Mouse')
    assert plugin.supports_device('Trackpad Device')
    assert not plugin.supports_device('Xbox Controller')


def test_create_pipeline_returns_wired_pair() -> None:
    plugin = KeyboardMouseInputPlugin()
    store = ProfileStore()
    listener = FakeOSListener()
    ingestion, mapping = plugin.create_pipeline(
        profile_store=store,
        listener=listener,
    )
    assert ingestion is not None
    assert mapping is not None


def test_create_pipeline_events_flow_through() -> None:
    plugin = KeyboardMouseInputPlugin()
    store = ProfileStore()
    store.create('Default')
    listener = FakeOSListener()

    ingestion, mapping = plugin.create_pipeline(
        profile_store=store,
        listener=listener,
    )

    received = []
    mapping.subscribe(received.append)
    ingestion.start()

    listener.push(
        InputEvent(
            kind=InputEventKind.KEY_PRESS,
            device_family='keyboard-mouse',
            timestamp_ns=1000,
            key='KEY_A',
        )
    )
    assert len(received) == 1
    assert dict(received[0].controls).get('KEY_A') is True


def _make_pynput_mocks() -> tuple[MagicMock, MagicMock, MagicMock, MagicMock]:
    """Return (mock_kb_module, mock_mouse_module, mock_kb_listener, mock_mouse_listener)."""
    mock_kb_listener = MagicMock()
    mock_mouse_listener = MagicMock()

    mock_kb = ModuleType('pynput.keyboard')
    mock_kb.Listener = MagicMock(return_value=mock_kb_listener)

    mock_mouse = ModuleType('pynput.mouse')
    mock_mouse.Listener = MagicMock(return_value=mock_mouse_listener)

    return mock_kb, mock_mouse, mock_kb_listener, mock_mouse_listener


def test_pynput_listener_start_stop() -> None:
    from aetherflow.input.kbm import PynputOSListener

    mock_kb, mock_mouse, mock_kb_listener, mock_mouse_listener = _make_pynput_mocks()

    with patch.dict(sys.modules, {'pynput.keyboard': mock_kb, 'pynput.mouse': mock_mouse}):
        pynput_listener = PynputOSListener()
        pynput_listener.start(on_event=lambda _: None)

        mock_kb.Listener.assert_called_once()
        mock_mouse.Listener.assert_called_once()
        mock_kb_listener.start.assert_called_once()
        mock_mouse_listener.start.assert_called_once()

        pynput_listener.stop()
        mock_kb_listener.stop.assert_called_once()
        mock_mouse_listener.stop.assert_called_once()


def test_pynput_listener_degrades_gracefully_on_headless() -> None:
    from aetherflow.input.kbm import PynputOSListener

    with patch.dict(sys.modules, {'pynput.keyboard': None, 'pynput.mouse': None}):  # type: ignore[dict-item]
        pynput_listener = PynputOSListener()
        # Should not raise even with no desktop backend
        pynput_listener.start(on_event=lambda _: None)
        assert pynput_listener._kb_listener is None
        assert pynput_listener._mouse_listener is None
