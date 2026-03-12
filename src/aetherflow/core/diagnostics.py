"""Runtime diagnostics helpers for input and output telemetry."""

from __future__ import annotations

import math
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PipelineDiagnostics:
    """Controller pipeline telemetry snapshot."""

    event_rate_hz: float
    output_rate_hz: float
    latency_ms: float
    jitter_ms: float

    def as_dict(self) -> dict[str, float]:
        """Return a JSON-serializable diagnostics payload."""
        return {
            'event_rate_hz': self.event_rate_hz,
            'output_rate_hz': self.output_rate_hz,
            'latency_ms': self.latency_ms,
            'jitter_ms': self.jitter_ms,
        }


class PipelineDiagnosticsTracker:
    """Track pipeline telemetry over a rolling window."""

    def __init__(
        self,
        *,
        window_seconds: float = 5.0,
        now: Callable[[], float] | None = None,
    ) -> None:
        """Initialize the diagnostics tracker.

        Args:
            window_seconds: Rolling window length in seconds.
            now: Optional clock function returning monotonic seconds.

        """
        self._window_seconds = window_seconds
        self._now = now or time.monotonic
        self._event_times: deque[float] = deque()
        self._output_times: deque[float] = deque()
        self._latency_samples: deque[tuple[float, float]] = deque()

    def record_event(self) -> None:
        """Record a pipeline input event."""
        now = self._now()
        self._event_times.append(now)
        self._prune(now)

    def record_output(self) -> None:
        """Record a pipeline output emission."""
        now = self._now()
        self._output_times.append(now)
        self._prune(now)

    def record_latency(self, latency_ms: float) -> None:
        """Record a latency sample in milliseconds.

        Args:
            latency_ms: Measured latency in milliseconds.

        """
        now = self._now()
        self._latency_samples.append((now, latency_ms))
        self._prune(now)

    def snapshot(self) -> PipelineDiagnostics:
        """Return the current diagnostics snapshot.

        Returns:
            Snapshot of event rates, output rates, latency, and jitter.

        """
        now = self._now()
        self._prune(now)
        event_rate = self._rate(len(self._event_times))
        output_rate = self._rate(len(self._output_times))
        latency_ms, jitter_ms = self._latency_and_jitter()
        return PipelineDiagnostics(
            event_rate_hz=event_rate,
            output_rate_hz=output_rate,
            latency_ms=latency_ms,
            jitter_ms=jitter_ms,
        )

    def _rate(self, count: int) -> float:
        """Calculate rate per second for the rolling window.

        Args:
            count: Number of samples within the window.

        Returns:
            Rate in Hz for the configured window.

        """
        if self._window_seconds <= 0:
            return 0.0
        return count / self._window_seconds

    def _latency_and_jitter(self) -> tuple[float, float]:
        """Compute latency mean and jitter percentile.

        Returns:
            Tuple of latency mean and jitter percentile.

        """
        if not self._latency_samples:
            return 0.0, 0.0
        latencies = [sample[1] for sample in self._latency_samples]
        latency_ms = sum(latencies) / len(latencies)
        if len(latencies) < 2:
            return latency_ms, 0.0
        deltas = [
            abs(latencies[index] - latencies[index - 1])
            for index in range(1, len(latencies))
        ]
        jitter_ms = self._percentile(deltas, 95.0)
        return latency_ms, jitter_ms

    def _percentile(self, values: list[float], percentile: float) -> float:
        """Return a percentile value from a list of samples.

        Args:
            values: Sample values to evaluate.
            percentile: Percentile to compute (0-100).

        Returns:
            Percentile value, or 0 when empty.

        """
        if not values:
            return 0.0
        ordered = sorted(values)
        rank = math.ceil((percentile / 100.0) * len(ordered)) - 1
        index = max(0, min(rank, len(ordered) - 1))
        return ordered[index]

    def _prune(self, now: float) -> None:
        """Drop samples that fall outside the rolling window.

        Args:
            now: Current monotonic time in seconds.

        """
        cutoff = now - self._window_seconds
        while self._event_times and self._event_times[0] < cutoff:
            self._event_times.popleft()
        while self._output_times and self._output_times[0] < cutoff:
            self._output_times.popleft()
        while self._latency_samples and self._latency_samples[0][0] < cutoff:
            self._latency_samples.popleft()
