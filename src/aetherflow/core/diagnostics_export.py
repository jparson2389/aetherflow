"""Diagnostics and success-metric collection."""

from __future__ import annotations

import json
from pathlib import Path


class DiagnosticsExporter:
    """Build diagnostics export payloads."""

    def export(self) -> dict[str, object]:
        """Return a minimal diagnostics payload."""
        return {
            "plugins": [],
            "workers": [],
            "envs": [],
            "logs": {"recent": []},
            "system": {"platform": "windows"},
            "overflow_counters": {"frame_overflows": 0},
            "restart_counters": {"worker_restarts": 0},
        }

    def write_report(self, path: Path) -> None:
        """Write a diagnostics report to disk."""
        payload = self.export()
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


class SuccessMetrics:
    """Track onboarding timing metrics."""

    def __init__(self) -> None:
        """Initialize empty success-metric samples."""
        self._onboarding_times: list[int] = []

    def record_onboarding_time(self, seconds: int) -> None:
        """Record an onboarding run duration in seconds."""
        self._onboarding_times.append(seconds)

    def onboarding_within_target(self, *, target_seconds: int) -> bool:
        """Return whether all recorded onboarding runs meet the target."""
        return bool(self._onboarding_times) and all(
            duration <= target_seconds for duration in self._onboarding_times
        )

    def export_onboarding_report(self, path: Path) -> None:
        """Write onboarding timing evidence to disk."""
        payload = {
            "runs": list(self._onboarding_times),
            "within_target": self.onboarding_within_target(target_seconds=300),
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
