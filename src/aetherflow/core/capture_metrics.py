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
    duration_s: float = 0.0
    frames_total: int = 0
    drop_window_s: float = 0.0

    @property
    def drop_rate(self) -> float:
        """Return the dropped-frame rate over the reported window."""
        if self.frames_total <= 0:
            return 0.0
        return self.dropped_frames / self.frames_total

    @property
    def is_sustained_drop(self) -> bool:
        """Return whether the session violates sustained-drop thresholds."""
        fps_drop = (
            self.measured_fps < self.target_fps * 0.9 and self.duration_s >= 3.0
        )
        drop_rate_violation = self.drop_rate > 0.02 and self.drop_window_s >= 5.0
        return fps_drop or drop_rate_violation

    @property
    def is_stable(self) -> bool:
        """Return whether the capture session meets the stability target."""
        return not self.is_sustained_drop and self.jitter_ms <= 4.0

    def recommended_fallback(self) -> str:
        """Recommend a safer fallback mode."""
        if self.target_fps >= 120:
            return "1080p@60"
        return "720p@30"
