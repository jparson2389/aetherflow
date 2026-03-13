"""Diagnostics and success-metric collection."""

from __future__ import annotations

import json
from pathlib import Path

from loguru import logger


class DiagnosticsExporter:
    """Build diagnostics export payloads."""

    def __init__(self) -> None:
        """Initialize diagnostics collection state."""
        self._plugins: list[dict[str, object]] = []
        self._workers: list[dict[str, object]] = []
        self._envs: list[dict[str, object]] = []
        self._recent_logs: list[str] = []
        self._overflow_counters: dict[str, int] = {'frame_overflows': 0}
        self._restart_counters: dict[str, int] = {'worker_restarts': 0}
        self._system: dict[str, object] = {'platform': 'windows'}

    def add_plugin(self, payload: dict[str, object]) -> None:
        """Add a plugin payload entry.

        Args:
            payload: Plugin summary payload.

        """
        self._plugins.append(dict(payload))

    def add_worker(self, payload: dict[str, object]) -> None:
        """Add a worker payload entry.

        Args:
            payload: Worker summary payload.

        """
        self._workers.append(dict(payload))

    def add_env(self, payload: dict[str, object]) -> None:
        """Add an environment payload entry.

        Args:
            payload: Environment summary payload.

        """
        self._envs.append(dict(payload))

    def record_log(self, message: str) -> None:
        """Record a recent log message.

        Args:
            message: Log message to include in diagnostics.

        """
        self._recent_logs.append(message)

    def record_overflow(self, *, count: int = 1) -> None:
        """Record frame overflow counters.

        Args:
            count: Number of overflow events to add.

        """
        self._overflow_counters['frame_overflows'] += count

    def record_restart(self, *, count: int = 1) -> None:
        """Record worker restart counters.

        Args:
            count: Number of restart events to add.

        """
        self._restart_counters['worker_restarts'] += count

    def export(self) -> dict[str, object]:
        """Return a minimal diagnostics payload."""
        return {
            'plugins': list(self._plugins),
            'workers': list(self._workers),
            'envs': list(self._envs),
            'logs': {'recent': list(self._recent_logs)},
            'system': dict(self._system),
            'overflow_counters': dict(self._overflow_counters),
            'restart_counters': dict(self._restart_counters),
        }

    def write_report(self, path: Path) -> None:
        """Write a diagnostics report to disk."""
        payload = self.export()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
        logger.debug('Diagnostics report written to {}.', path)


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
            'runs': list(self._onboarding_times),
            'within_target': self.onboarding_within_target(target_seconds=300),
        }
        path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
