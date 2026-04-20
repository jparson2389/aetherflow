"""Mapping pipeline with latency telemetry."""

from __future__ import annotations

import statistics
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from aetherflow.core.diagnostics import PipelineDiagnostics, PipelineDiagnosticsTracker
from aetherflow.core.profiles import ProfileStore
from aetherflow.input.events import InputEvent, InputEventKind, MappedEvent
from aetherflow.input.pipeline import DeviceIngestionPipeline


@dataclass(slots=True)
class InputLatencyTelemetry:
    """Rolling-window latency tracker for the mapping pipeline."""

    window_size: int = 256
    _samples: list[float] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def record(self, latency_ns: int) -> None:
        """Record a latency sample in nanoseconds.

        Args:
            latency_ns: Pipeline traversal time in nanoseconds.

        """
        ms = latency_ns / 1_000_000
        with self._lock:
            if len(self._samples) >= self.window_size:
                self._samples.pop(0)
            self._samples.append(ms)

    @property
    def mean_ms(self) -> float:
        """Return mean latency in milliseconds."""
        with self._lock:
            samples = list(self._samples)
        if not samples:
            return 0.0
        return statistics.mean(samples)

    @property
    def p99_ms(self) -> float:
        """Return p99 latency in milliseconds."""
        with self._lock:
            samples = list(self._samples)
        if len(samples) < 2:
            return 0.0
        return statistics.quantiles(samples, n=100)[-1]

    @property
    def sample_count(self) -> int:
        """Return the number of recorded samples."""
        with self._lock:
            return len(self._samples)

    def reset(self) -> None:
        """Clear all samples."""
        with self._lock:
            self._samples.clear()


def _event_to_raw(event: InputEvent) -> dict[str, bool | float]:
    """Convert an InputEvent to the raw dict that InputProfile.translate() expects.

    Args:
        event: The input event to convert.

    Returns:
        A dict mapping control names to values.

    """
    if event.kind in (InputEventKind.KEY_PRESS, InputEventKind.MOUSE_BUTTON_PRESS):
        return {event.key: True} if event.key else {}
    if event.kind in (InputEventKind.KEY_RELEASE, InputEventKind.MOUSE_BUTTON_RELEASE):
        return {event.key: False} if event.key else {}
    if event.kind is InputEventKind.MOUSE_MOVE and event.position:
        return {
            'MOUSE_X': float(event.position[0]),
            'MOUSE_Y': float(event.position[1]),
        }
    if event.kind is InputEventKind.MOUSE_SCROLL and event.delta:
        return {
            'SCROLL_DX': float(event.delta[0]),
            'SCROLL_DY': float(event.delta[1]),
        }
    return {}


class MappingPipeline:
    """Translates raw input events through the active profile with telemetry."""

    def __init__(
        self,
        *,
        ingestion: DeviceIngestionPipeline,
        profile_store: ProfileStore,
    ) -> None:
        """Wire into an ingestion pipeline.

        Args:
            ingestion: The upstream event source.
            profile_store: Profile store for the active mapping profile.

        """
        self._profile_store = profile_store
        self._telemetry = InputLatencyTelemetry()
        # Threading: _on_event is called from the OS listener thread (via
        # DeviceIngestionPipeline._dispatch); diagnostics_snapshot() may be
        # called from the UI/main thread.  PipelineDiagnosticsTracker is
        # internally locked to protect concurrent access.
        self._diagnostics = PipelineDiagnosticsTracker()
        self._subscribers: list[Callable[[MappedEvent], None]] = []
        self._lock = threading.Lock()
        ingestion.subscribe(self._on_event)

    @property
    def telemetry(self) -> InputLatencyTelemetry:
        """Return the latency telemetry tracker."""
        return self._telemetry

    def diagnostics_snapshot(self) -> PipelineDiagnostics:
        """Return the current controller pipeline diagnostics snapshot.

        Returns:
            Snapshot of current event/output rates, latency, and jitter.

        """
        return self._diagnostics.snapshot()

    def subscribe(self, handler: Callable[[MappedEvent], None]) -> None:
        """Register a mapped-event handler.

        Args:
            handler: Callable invoked for each translated event.

        """
        with self._lock:
            self._subscribers.append(handler)

    def unsubscribe(self, handler: Callable[[MappedEvent], None]) -> None:
        """Remove a previously registered handler.

        Args:
            handler: The handler to remove.

        """
        with self._lock:
            try:
                self._subscribers.remove(handler)
            except ValueError:
                pass

    def _on_event(self, event: InputEvent) -> None:
        """Translate and dispatch an input event.

        Args:
            event: Raw input event from the ingestion pipeline.

        """
        active_id = self._profile_store.active_profile_id
        if active_id is None:
            return
        profile = self._profile_store.profiles.get(active_id)
        if profile is None:
            return

        raw = _event_to_raw(event)
        if not raw:
            return

        self._diagnostics.record_event()
        start_ns = time.monotonic_ns()
        controls_dict = profile.translate(raw)
        end_ns = time.monotonic_ns()

        latency_ns = end_ns - start_ns
        self._telemetry.record(latency_ns)
        self._diagnostics.record_latency(latency_ns / 1_000_000)

        mapped = MappedEvent(
            source=event,
            controls=tuple(controls_dict.items()),
            latency_ns=latency_ns,
        )

        with self._lock:
            subscribers = list(self._subscribers)
        for handler in subscribers:
            handler(mapped)
        self._diagnostics.record_output()
