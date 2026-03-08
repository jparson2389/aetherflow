"""Capture telemetry helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class CaptureMetrics:
    """Capture stability metrics."""

    target_fps: int
    measured_fps: float
    dropped_frames: int
    jitter_ms: float

    @property
    def is_stable(self) -> bool:
        """Return whether the capture session meets the stability target."""
        return self.measured_fps >= self.target_fps * 0.9 and self.jitter_ms <= 4.0

    def recommended_fallback(self) -> str:
        """Recommend a safer fallback mode."""
        if self.target_fps >= 120:
            return "1080p@60"
        return "720p@30"
