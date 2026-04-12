"""Capture telemetry helpers."""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field


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
        fps_drop = self.measured_fps < self.target_fps * 0.9 and self.duration_s >= 3.0
        drop_rate_violation = self.drop_rate > 0.02 and self.drop_window_s >= 5.0
        return fps_drop or drop_rate_violation

    @property
    def is_stable(self) -> bool:
        """Return whether the capture session meets the stability target."""
        return not self.is_sustained_drop and self.jitter_ms <= 4.0

    def recommended_fallback(self) -> str:
        """Recommend a safer fallback mode."""
        if self.target_fps >= 120:
            return '1080p@60'
        return '720p@30'


@dataclass(slots=True)
class CaptureMetricsTracker:
    """Track capture samples over a rolling window."""

    window_seconds: float = 5.0
    now: Callable[[], float] = time.monotonic
    _frames: deque[float] = field(default_factory=deque)
    _drops: deque[float] = field(default_factory=deque)

    def record_frame(
        self, *, timestamp_s: float | None = None, dropped: bool = False
    ) -> None:
        """Record a delivered or dropped frame sample."""
        sample_time = self.now() if timestamp_s is None else timestamp_s
        if dropped:
            self._drops.append(sample_time)
        else:
            self._frames.append(sample_time)
        self._prune(sample_time)

    def snapshot(self, *, target_fps: int) -> CaptureMetrics:
        """Build a metrics snapshot for the active rolling window."""
        sample_time = self._reference_time()
        self._prune(sample_time)
        measured_fps, duration_s = self._measured_fps()
        delivered_frames = len(self._frames)
        dropped_frames = len(self._drops)
        frames_total = delivered_frames + dropped_frames
        return CaptureMetrics(
            target_fps=target_fps,
            measured_fps=measured_fps,
            dropped_frames=dropped_frames,
            jitter_ms=self._jitter_ms(target_fps=target_fps),
            duration_s=duration_s,
            frames_total=frames_total,
            drop_window_s=duration_s,
        )

    def _measured_fps(self) -> tuple[float, float]:
        """Return measured FPS and active sample duration."""
        if not self._frames:
            return 0.0, 0.0
        if len(self._frames) == 1:
            return 0.0, 0.0
        duration_s = self._frames[-1] - self._frames[0]
        if duration_s <= 0.0:
            return 0.0, 0.0
        return len(self._frames) / duration_s, duration_s

    def _jitter_ms(self, *, target_fps: int) -> float:
        """Return a simple mean frame-interval jitter in milliseconds."""
        if len(self._frames) < 2 or target_fps <= 0:
            return 0.0
        expected_interval = 1.0 / target_fps
        deltas = []
        previous = None
        for timestamp in self._frames:
            if previous is not None:
                deltas.append(abs((timestamp - previous) - expected_interval) * 1000.0)
            previous = timestamp
        if not deltas:
            return 0.0
        return sum(deltas) / len(deltas)

    def _reference_time(self) -> float:
        """Return the most recent sample time, falling back to the clock."""
        samples = []
        if self._frames:
            samples.append(self._frames[-1])
        if self._drops:
            samples.append(self._drops[-1])
        if samples:
            return max(samples)
        return self.now()

    def _prune(self, now_s: float) -> None:
        """Discard samples outside the configured rolling window."""
        cutoff = now_s - self.window_seconds
        while self._frames and self._frames[0] < cutoff:
            self._frames.popleft()
        while self._drops and self._drops[0] < cutoff:
            self._drops.popleft()
