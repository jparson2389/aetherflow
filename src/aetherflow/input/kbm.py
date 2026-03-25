"""Keyboard and mouse input plugin with real OS event ingestion."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TYPE_CHECKING, ClassVar

from loguru import logger

from aetherflow.core.profiles import ProfileStore
from aetherflow.input.events import InputEvent, InputEventKind
from aetherflow.input.listener import OSListenerProtocol
from aetherflow.input.mapping import MappingPipeline
from aetherflow.input.pipeline import DeviceIngestionPipeline

if TYPE_CHECKING:
    import pynput.keyboard
    import pynput.mouse


class PynputOSListener:
    """OS listener backed by pynput for keyboard and mouse events."""

    def __init__(self) -> None:
        """Initialise with no active listeners."""
        self._kb_listener: pynput.keyboard.Listener | None = None
        self._mouse_listener: pynput.mouse.Listener | None = None
        self._callback: Callable[[InputEvent], None] | None = None

    def start(self, on_event: Callable[[InputEvent], None]) -> None:
        """Spawn pynput keyboard and mouse listeners.

        Degrades gracefully to a no-op when no desktop backend is available
        (headless CI, Wayland without XWayland, SSH sessions without -X).

        Args:
            on_event: Callback invoked for each OS input event.

        """
        try:
            import pynput.keyboard
            import pynput.mouse
        except Exception:  # ImportError or backend connection failure (headless)
            logger.warning(
                'PynputOSListener: no desktop backend available; '
                'keyboard/mouse ingestion disabled.'
            )
            return

        self._callback = on_event

        self._kb_listener = pynput.keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._mouse_listener = pynput.mouse.Listener(
            on_move=self._on_move,
            on_click=self._on_click,
            on_scroll=self._on_scroll,
        )
        self._kb_listener.start()
        self._mouse_listener.start()

    def stop(self) -> None:
        """Stop both listeners and join their threads."""
        if self._kb_listener is not None:
            self._kb_listener.stop()
            self._kb_listener.join(timeout=0.1)
        if self._mouse_listener is not None:
            self._mouse_listener.stop()
            self._mouse_listener.join(timeout=0.1)
        self._callback = None

    def _emit(self, event: InputEvent) -> None:
        """Deliver an event to the registered callback.

        Args:
            event: The input event to deliver.

        """
        if self._callback is not None:
            self._callback(event)

    def _on_press(
        self, key: pynput.keyboard.Key | pynput.keyboard.KeyCode | None
    ) -> None:
        """Handle a key press event.

        Args:
            key: pynput key object, or None for unrecognised keys.

        """
        if key is None:
            return
        self._emit(
            InputEvent(
                kind=InputEventKind.KEY_PRESS,
                device_family='keyboard-mouse',
                timestamp_ns=time.monotonic_ns(),
                key=_key_name(key),
            )
        )

    def _on_release(
        self, key: pynput.keyboard.Key | pynput.keyboard.KeyCode | None
    ) -> None:
        """Handle a key release event.

        Args:
            key: pynput key object, or None for unrecognised keys.

        """
        if key is None:
            return
        self._emit(
            InputEvent(
                kind=InputEventKind.KEY_RELEASE,
                device_family='keyboard-mouse',
                timestamp_ns=time.monotonic_ns(),
                key=_key_name(key),
            )
        )

    def _on_move(self, x: int, y: int) -> None:
        """Handle a mouse move event.

        Args:
            x: Cursor x position.
            y: Cursor y position.

        """
        self._emit(
            InputEvent(
                kind=InputEventKind.MOUSE_MOVE,
                device_family='keyboard-mouse',
                timestamp_ns=time.monotonic_ns(),
                position=(x, y),
            )
        )

    def _on_click(
        self, _x: int, _y: int, button: pynput.mouse.Button, pressed: bool
    ) -> None:
        """Handle a mouse click event.

        Args:
            _x: Cursor x position (unused).
            _y: Cursor y position (unused).
            button: pynput button object.
            pressed: Whether the button was pressed or released.

        """
        kind = (
            InputEventKind.MOUSE_BUTTON_PRESS
            if pressed
            else InputEventKind.MOUSE_BUTTON_RELEASE
        )
        self._emit(
            InputEvent(
                kind=kind,
                device_family='keyboard-mouse',
                timestamp_ns=time.monotonic_ns(),
                key=f'MOUSE_{button.name.upper()}',
            )
        )

    def _on_scroll(self, _x: int, _y: int, dx: int, dy: int) -> None:
        """Handle a mouse scroll event.

        Args:
            _x: Cursor x position (unused).
            _y: Cursor y position (unused).
            dx: Horizontal scroll delta.
            dy: Vertical scroll delta.

        """
        self._emit(
            InputEvent(
                kind=InputEventKind.MOUSE_SCROLL,
                device_family='keyboard-mouse',
                timestamp_ns=time.monotonic_ns(),
                delta=(dx, dy),
            )
        )


def _key_name(key: pynput.keyboard.Key | pynput.keyboard.KeyCode | None) -> str:
    """Convert a pynput key to a stable string name.

    Args:
        key: pynput Key or KeyCode object.

    Returns:
        A normalised key name string.

    """
    import pynput.keyboard

    if key is None:
        return 'KEY_UNKNOWN'
    if isinstance(key, pynput.keyboard.KeyCode):
        if key.char is not None:
            return f'KEY_{key.char.upper()}'
        if key.vk is not None:
            return f'SCANCODE_{key.vk}'
        return 'KEY_UNKNOWN'
    # pynput.keyboard.Key enum
    return f'KEY_{key.name.upper()}'


class KeyboardMouseInputPlugin:
    """KBM input plugin with OS listener and pipeline factory."""

    plugin_id: ClassVar[str] = 'input.kbm'
    device_family: ClassVar[str] = 'keyboard-mouse'
    _supported_signatures: ClassVar[tuple[str, ...]] = (
        'keyboard',
        'mouse',
        'trackpad',
    )

    def supports_device(self, signature: str) -> bool:
        """Return whether a device signature matches keyboard/mouse inputs.

        Args:
            signature: Device identifier string.

        Returns:
            True when the signature matches known keyboard/mouse tokens.

        """
        normalized = signature.lower()
        return any(token in normalized for token in self._supported_signatures)

    def create_pipeline(
        self,
        profile_store: ProfileStore,
        *,
        listener: OSListenerProtocol | None = None,
    ) -> tuple[DeviceIngestionPipeline, MappingPipeline]:
        """Create a wired ingestion and mapping pipeline.

        Args:
            profile_store: Profile store for active mapping profiles.
            listener: Optional OS listener override (defaults to pynput).

        Returns:
            Tuple of (ingestion_pipeline, mapping_pipeline).

        """
        resolved_listener = listener or PynputOSListener()
        ingestion = DeviceIngestionPipeline(listener=resolved_listener)
        mapping = MappingPipeline(
            ingestion=ingestion,
            profile_store=profile_store,
        )
        return ingestion, mapping
