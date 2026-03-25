"""OS listener boundary for input device events."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from aetherflow.input.events import InputEvent


class OSListenerProtocol(Protocol):
    """Contract for OS-level input event listeners."""

    def start(self, on_event: Callable[[InputEvent], None]) -> None:
        """Begin listening for OS input events.

        Args:
            on_event: Callback invoked for each raw input event.

        """
        ...

    def stop(self) -> None:
        """Stop listening and release OS resources."""
        ...


class NullOSListener:
    """No-op listener for graceful degradation."""

    def start(self, on_event: Callable[[InputEvent], None]) -> None:
        """Accept the callback but never fire it.

        Args:
            on_event: Unused callback.

        """

    def stop(self) -> None:
        """No-op stop."""


class FakeOSListener:
    """Test double that accepts injected events via push().

    Args:
        on_event: Registered callback, set by start().

    """

    def __init__(self) -> None:
        """Initialise with no callback."""
        self._callback: Callable[[InputEvent], None] | None = None

    def start(self, on_event: Callable[[InputEvent], None]) -> None:
        """Register the event callback.

        Args:
            on_event: Callback to invoke on each pushed event.

        """
        self._callback = on_event

    def stop(self) -> None:
        """Clear the callback to prevent further delivery."""
        self._callback = None

    def push(self, event: InputEvent) -> None:
        """Inject a synthetic event for testing.

        Args:
            event: The event to deliver to the registered callback.

        """
        if self._callback is not None:
            self._callback(event)
