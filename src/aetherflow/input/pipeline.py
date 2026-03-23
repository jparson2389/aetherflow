"""Device ingestion pipeline with lifecycle management."""

from __future__ import annotations

import threading
from collections.abc import Callable
from enum import StrEnum

from aetherflow.input.events import InputEvent
from aetherflow.input.listener import OSListenerProtocol


class IngestionState(StrEnum):
    """Pipeline lifecycle states."""

    IDLE = 'idle'
    RUNNING = 'running'
    PAUSED = 'paused'
    STOPPED = 'stopped'


class DeviceIngestionPipeline:
    """Manages an OS listener and dispatches events to subscribers."""

    def __init__(self, *, listener: OSListenerProtocol) -> None:
        """Create a pipeline backed by the given OS listener.

        Args:
            listener: OS-level listener implementation.

        """
        self._listener = listener
        self._state = IngestionState.IDLE
        self._subscribers: list[Callable[[InputEvent], None]] = []
        self._lock = threading.Lock()

    @property
    def state(self) -> IngestionState:
        """Return the current lifecycle state."""
        with self._lock:
            return self._state

    def start(self) -> None:
        """Start the listener and begin dispatching events."""
        with self._lock:
            if self._state is IngestionState.STOPPED:
                raise RuntimeError('Cannot restart a stopped pipeline.')
            if self._state is IngestionState.RUNNING:
                return
            self._state = IngestionState.RUNNING
        self._listener.start(on_event=self._dispatch)

    def stop(self) -> None:
        """Stop the listener permanently."""
        with self._lock:
            if self._state is IngestionState.STOPPED:
                return
            self._state = IngestionState.STOPPED
        self._listener.stop()

    def pause(self) -> None:
        """Pause event delivery without stopping the listener."""
        with self._lock:
            if self._state is IngestionState.RUNNING:
                self._state = IngestionState.PAUSED

    def resume(self) -> None:
        """Resume event delivery after a pause."""
        with self._lock:
            if self._state is IngestionState.PAUSED:
                self._state = IngestionState.RUNNING

    def subscribe(self, handler: Callable[[InputEvent], None]) -> None:
        """Register an event handler.

        Args:
            handler: Callable invoked for each dispatched event.

        """
        with self._lock:
            self._subscribers.append(handler)

    def unsubscribe(self, handler: Callable[[InputEvent], None]) -> None:
        """Remove a previously registered handler.

        Args:
            handler: The handler to remove.

        """
        with self._lock:
            try:
                self._subscribers.remove(handler)
            except ValueError:
                pass

    def _dispatch(self, event: InputEvent) -> None:
        """Forward an event to all subscribers if running.

        Args:
            event: The input event to dispatch.

        """
        with self._lock:
            if self._state is not IngestionState.RUNNING:
                return
            subscribers = list(self._subscribers)
        for handler in subscribers:
            handler(event)
