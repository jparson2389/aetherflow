"""Diagnostics and success-metric collection."""

from __future__ import annotations


class DiagnosticsExporter:
    """Build diagnostics export payloads."""

    def export(self) -> dict[str, object]:
        """Return a minimal diagnostics payload."""
        return {
            "plugins": [],
            "workers": [],
            "envs": [],
            "system": {"platform": "windows"},
        }


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
