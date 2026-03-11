"""Runtime diagnostics helpers for input and output telemetry."""

from __future__ import annotations

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
